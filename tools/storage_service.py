"""
Storage Service for Creative Intelligence Studio.
Provides unified persistence with:
- Google Cloud Firestore for Director Manifests ("Your Content") & Creator DNA
- Google Cloud Storage for Character Anchors & Omni Reference Renders
- Seamless local filesystem fallback for offline/local development
"""

from __future__ import annotations

from datetime import date, datetime
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("studio_storage")


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """Safe json serializer handling datetime and Firestore objects without crashing."""
    def _default(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return str(o)
    return json.dumps(obj, indent=indent, default=_default)


def sanitize_json_dict(data: Any) -> Any:
    """Recursively converts datetimes, enums, etc. to JSON-safe primitives."""
    if data is None:
        return None
    return json.loads(safe_json_dumps(data))

# Optional GCP imports with safe fallbacks
try:
    from google.cloud import firestore
    HAS_FIRESTORE = True
except ImportError:
    firestore = None  # type: ignore
    HAS_FIRESTORE = False

try:
    from google.cloud import storage
    HAS_STORAGE = True
except ImportError:
    storage = None  # type: ignore
    HAS_STORAGE = False

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_MANIFESTS_DIR = BASE_DIR / "corpus" / "director_output"
LOCAL_ANCHORS_DIR = BASE_DIR / "corpus" / "character_anchors"
LOCAL_RENDERS_DIR = BASE_DIR / "output" / "renders"
LOCAL_DATA_DIR = BASE_DIR / "corpus" / "data"

# Ensure local directories exist
LOCAL_MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_ANCHORS_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_RENDERS_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)


class StorageService:
    def __init__(self) -> None:
        self.project_id = (
            os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("GCP_PROJECT")
            or "content-intelligence-451200"
        )
        self.bucket_name = (
            os.getenv("MEDIA_BUCKET_NAME")
            or f"{self.project_id}-media"
        )

        self._firestore_client: Optional[Any] = None
        self._firestore_initialized = False

        self._storage_client: Optional[Any] = None
        self._storage_bucket: Optional[Any] = None
        self._storage_initialized = False

    # -------------------------------------------------------------------------
    # Clients initialization
    # -------------------------------------------------------------------------

    def get_firestore(self) -> Optional[Any]:
        if self._firestore_initialized:
            return self._firestore_client

        self._firestore_initialized = True
        if not HAS_FIRESTORE:
            logger.info("[StorageService] google-cloud-firestore not installed; using local disk.")
            return None

        try:
            # On Cloud Run / GCP, Default Application Credentials (ADC) are automatically picked up.
            self._firestore_client = firestore.Client(project=self.project_id)
            logger.info(f"[StorageService] Connected to Firestore project '{self.project_id}'.")
        except Exception as e:
            logger.info(f"[StorageService] Firestore unavailable ({e}); falling back to local files.")
            self._firestore_client = None

        return self._firestore_client

    def get_storage_bucket(self) -> Optional[Any]:
        if self._storage_initialized:
            return self._storage_bucket

        self._storage_initialized = True
        if not HAS_STORAGE:
            logger.info("[StorageService] google-cloud-storage not installed; using local disk.")
            return None

        try:
            self._storage_client = storage.Client(project=self.project_id)
            self._storage_bucket = self._storage_client.bucket(self.bucket_name)
            logger.info(f"[StorageService] Connected to GCS bucket '{self.bucket_name}'.")
        except Exception as e:
            logger.info(f"[StorageService] Cloud Storage unavailable ({e}); falling back to local disk.")
            self._storage_bucket = None

        return self._storage_bucket

    @staticmethod
    def sanitize_session_id(session_id: Optional[str]) -> str:
        if not session_id or not session_id.strip():
            return "default"
        return "".join(c for c in session_id.strip() if c.isalnum() or c in ("-", "_"))

    # -------------------------------------------------------------------------
    # Director Manifests ("Your Content")
    # -------------------------------------------------------------------------

    def save_manifest(
        self,
        manifest_data: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Saves a director manifest to Firestore and mirrors it to the local cache.
        Firestore collection: users/{session_id}/manifests/{project_id}
        """
        safe_sess = self.sanitize_session_id(session_id)
        project_id = str(manifest_data.get("project_id") or "proj_edited").strip()
        filename = f"{project_id}.json"

        # 1. Save to local disk cache
        local_dir = LOCAL_MANIFESTS_DIR / safe_sess
        local_dir.mkdir(parents=True, exist_ok=True)
        local_file = local_dir / filename
        clean_manifest = sanitize_json_dict(manifest_data)
        local_file.write_text(safe_json_dumps(clean_manifest, indent=2), encoding="utf-8")

        # 2. Persist to Firestore if available
        db = self.get_firestore()
        firestore_synced = False
        if db is not None:
            try:
                doc_ref = (
                    db.collection("users")
                    .document(safe_sess)
                    .collection("manifests")
                    .document(project_id)
                )
                payload = {
                    "project_id": project_id,
                    "title": manifest_data.get("title", project_id),
                    "total_target_duration_sec": float(manifest_data.get("total_target_duration_sec", 10.0)),
                    "shots_count": len(manifest_data.get("shots", [])),
                    "aspect_ratio": manifest_data.get("aspect_ratio", "9:16"),
                    "manifest": manifest_data,
                    "updated_at": firestore.SERVER_TIMESTAMP if firestore else None,
                }
                doc_ref.set(payload)
                firestore_synced = True
                logger.info(f"[StorageService] Manifest '{project_id}' persisted to Firestore for user '{safe_sess}'.")
            except Exception as e:
                logger.warning(f"[StorageService] Failed saving manifest to Firestore: {e}")

        return {
            "status": "success",
            "filename": filename,
            "project_id": project_id,
            "firestore_synced": firestore_synced,
            "manifest": manifest_data,
        }

    def list_manifests(self, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """
        Lists all manifests for the given user session.
        Merges results from Firestore and local cache to ensure high availability.
        """
        safe_sess = self.sanitize_session_id(session_id)
        items_by_id: Dict[str, Dict[str, Any]] = {}

        # 1. Fetch from Firestore if available
        db = self.get_firestore()
        if db is not None:
            try:
                coll_ref = db.collection("users").document(safe_sess).collection("manifests")
                docs = coll_ref.stream()
                for doc in docs:
                    data = doc.to_dict() or {}
                    manifest = data.get("manifest", {})
                    p_id = data.get("project_id", doc.id)
                    items_by_id[p_id] = {
                        "filename": f"{doc.id}.json",
                        "project_id": p_id,
                        "title": data.get("title") or manifest.get("title") or doc.id,
                        "total_target_duration_sec": float(
                            data.get("total_target_duration_sec") or manifest.get("total_target_duration_sec", 10.0)
                        ),
                        "shots_count": int(
                            data.get("shots_count") or len(manifest.get("shots", []))
                        ),
                        "aspect_ratio": data.get("aspect_ratio") or manifest.get("aspect_ratio", "9:16"),
                    }
            except Exception as e:
                logger.warning(f"[StorageService] Failed listing manifests from Firestore: {e}")

        # 2. Merge local manifests
        local_dir = LOCAL_MANIFESTS_DIR / safe_sess
        if local_dir.exists():
            for p in sorted(local_dir.glob("*.json")):
                p_id = p.stem
                if p_id not in items_by_id:
                    try:
                        content = json.loads(p.read_text(encoding="utf-8"))
                        items_by_id[p_id] = {
                            "filename": p.name,
                            "project_id": content.get("project_id", p_id),
                            "title": content.get("title", p_id),
                            "total_target_duration_sec": float(content.get("total_target_duration_sec", 10.0)),
                            "shots_count": len(content.get("shots", [])),
                            "aspect_ratio": content.get("aspect_ratio", "9:16"),
                        }
                    except Exception as e:
                        logger.warning(f"[StorageService] Failed reading local manifest {p.name}: {e}")

        return list(items_by_id.values())

    def get_manifest(self, filename_or_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves a manifest by filename (e.g. 'proj_123.json') or project_id.
        """
        safe_sess = self.sanitize_session_id(session_id)
        clean_id = filename_or_id[:-5] if filename_or_id.endswith(".json") else filename_or_id

        # 1. Try Firestore
        db = self.get_firestore()
        if db is not None:
            try:
                doc = (
                    db.collection("users")
                    .document(safe_sess)
                    .collection("manifests")
                    .document(clean_id)
                    .get()
                )
                if doc.exists:
                    doc_data = doc.to_dict() or {}
                    manifest = doc_data.get("manifest")
                    if manifest and isinstance(manifest, dict):
                        # Cache locally for faster subsequent access
                        clean_manifest = sanitize_json_dict(manifest)
                        local_cache = LOCAL_MANIFESTS_DIR / safe_sess / f"{clean_id}.json"
                        local_cache.parent.mkdir(parents=True, exist_ok=True)
                        local_cache.write_text(safe_json_dumps(clean_manifest, indent=2), encoding="utf-8")
                        return clean_manifest
            except Exception as e:
                logger.warning(f"[StorageService] Failed reading manifest from Firestore: {e}")

        # 2. Try user-scoped local file
        user_local = LOCAL_MANIFESTS_DIR / safe_sess / f"{clean_id}.json"
        if user_local.exists():
            try:
                return json.loads(user_local.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"[StorageService] Failed parsing user manifest {user_local}: {e}")

        # 3. Fallback to global sample manifests
        global_local = LOCAL_MANIFESTS_DIR / f"{clean_id}.json"
        if global_local.exists():
            try:
                return json.loads(global_local.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"[StorageService] Failed parsing global manifest {global_local}: {e}")

        return None

    # -------------------------------------------------------------------------
    # Character Anchors (Photos)
    # -------------------------------------------------------------------------

    def save_character_anchor(
        self,
        session_id: Optional[str],
        filename: str,
        content: bytes,
        content_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Saves character anchor photo to local disk and uploads to Google Cloud Storage.
        GCS path: gs://{bucket}/anchors/{session_id}/{filename}
        """
        safe_sess = self.sanitize_session_id(session_id)
        local_dir = LOCAL_ANCHORS_DIR / safe_sess
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / filename
        local_path.write_bytes(content)

        gcs_url: Optional[str] = None
        bucket = self.get_storage_bucket()
        if bucket is not None:
            try:
                blob_name = f"anchors/{safe_sess}/{filename}"
                blob = bucket.blob(blob_name)
                blob.upload_from_string(content, content_type=content_type)
                gcs_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
                logger.info(f"[StorageService] Character anchor uploaded to GCS: {blob_name}")
            except Exception as e:
                logger.warning(f"[StorageService] Failed uploading anchor to GCS: {e}")

        return {
            "status": "success",
            "filename": filename,
            "local_path": str(local_path.resolve()),
            "photo_url": f"/anchors/{safe_sess}/{filename}",
            "gcs_url": gcs_url,
        }

    def get_character_anchor(
        self,
        session_id: Optional[str],
        filename: str,
    ) -> Optional[Tuple[bytes, str]]:
        """
        Retrieves character anchor photo bytes and mime type.
        Checks local disk first; if not present, downloads from GCS and caches locally.
        """
        safe_sess = self.sanitize_session_id(session_id)
        local_path = LOCAL_ANCHORS_DIR / safe_sess / filename

        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "image/jpeg"

        if local_path.exists():
            return local_path.read_bytes(), mime_type

        # Check default avatar fallback
        if filename in ("default_avatar.png", "default_avatar.jpg"):
            demo_avatar = BASE_DIR / "corpus" / "character_anchors" / filename
            if demo_avatar.exists():
                return demo_avatar.read_bytes(), mime_type

        # Fetch from GCS
        bucket = self.get_storage_bucket()
        if bucket is not None:
            try:
                blob_name = f"anchors/{safe_sess}/{filename}"
                blob = bucket.blob(blob_name)
                if blob.exists():
                    data = blob.download_as_bytes()
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_bytes(data)
                    return data, (blob.content_type or mime_type)
            except Exception as e:
                logger.warning(f"[StorageService] Failed fetching anchor from GCS: {e}")

        return None

    # -------------------------------------------------------------------------
    # Reference Videos (Omni Renders)
    # -------------------------------------------------------------------------

    def save_reference_video(
        self,
        session_id: Optional[str],
        filename: str,
        local_video_path: str,
    ) -> Dict[str, Any]:
        """
        Uploads rendered reference video to Google Cloud Storage.
        GCS path: gs://{bucket}/renders/{session_id}/{filename}
        """
        safe_sess = self.sanitize_session_id(session_id)
        gcs_url: Optional[str] = None
        bucket = self.get_storage_bucket()

        if bucket is not None and Path(local_video_path).exists():
            try:
                blob_name = f"renders/{safe_sess}/{filename}"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(local_video_path, content_type="video/mp4")
                gcs_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
                logger.info(f"[StorageService] Reference video uploaded to GCS: {blob_name}")
            except Exception as e:
                logger.warning(f"[StorageService] Failed uploading reference video to GCS: {e}")

        return {
            "status": "success",
            "filename": filename,
            "local_path": local_video_path,
            "video_url": f"/renders/{safe_sess}/{filename}",
            "gcs_url": gcs_url,
        }

    def get_reference_video(
        self,
        session_id: Optional[str],
        filename: str,
    ) -> Optional[Tuple[bytes, str]]:
        """
        Retrieves reference video bytes. Checks local disk first, then GCS.
        """
        safe_sess = self.sanitize_session_id(session_id)
        local_path = LOCAL_RENDERS_DIR / safe_sess / filename

        if local_path.exists():
            return local_path.read_bytes(), "video/mp4"

        # Check root renders dir
        root_render = LOCAL_RENDERS_DIR / filename
        if root_render.exists():
            return root_render.read_bytes(), "video/mp4"

        # Fetch from GCS
        bucket = self.get_storage_bucket()
        if bucket is not None:
            try:
                blob_name = f"renders/{safe_sess}/{filename}"
                blob = bucket.blob(blob_name)
                if blob.exists():
                    data = blob.download_as_bytes()
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_bytes(data)
                    return data, "video/mp4"
            except Exception as e:
                logger.warning(f"[StorageService] Failed fetching video from GCS: {e}")

        return None

    # -------------------------------------------------------------------------
    # Video Analyses (Corpus & User Uploads in Firestore & GCS)
    # -------------------------------------------------------------------------

    def save_analysis(
        self,
        analysis_data: Dict[str, Any],
        video_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persists a video analysis to Firestore and mirrors it to corpus/data.
        Firestore collection: analyses/{video_id}
        """
        vid = str(video_id or analysis_data.get("video_id") or "analyzed_video").strip()
        filename = f"{vid}.json"

        clean_data = sanitize_json_dict(analysis_data)

        # 1. Save to local disk cache (ensuring directory exists)
        local_dir = BASE_DIR / "corpus" / "data"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_file = local_dir / filename
        local_file.write_text(safe_json_dumps(clean_data, indent=2), encoding="utf-8")

        # 2. Persist to Firestore if available
        db = self.get_firestore()
        firestore_synced = False
        if db is not None:
            try:
                doc_ref = db.collection("analyses").document(vid)
                doc_ref.set(clean_data)
                firestore_synced = True
                logger.info(f"[StorageService] Analysis '{vid}' persisted to Firestore.")
            except Exception as e:
                logger.warning(f"[StorageService] Failed saving analysis to Firestore: {e}")

        # 3. Mirror to GCS bucket if available
        bucket = self.get_storage_bucket()
        if bucket is not None:
            try:
                blob = bucket.blob(f"analyses/{filename}")
                blob.upload_from_string(safe_json_dumps(clean_data, indent=2), content_type="application/json")
            except Exception as e:
                logger.debug(f"[StorageService] GCS analysis upload note: {e}")

        return {
            "status": "success",
            "video_id": vid,
            "filename": filename,
            "firestore_synced": firestore_synced,
        }

    def get_analysis(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a video analysis by video_id from local disk, Firestore, or GCS.
        """
        vid = video_id[:-5] if video_id.endswith(".json") else video_id

        # 1. Check local disk
        local_file = BASE_DIR / "corpus" / "data" / f"{vid}.json"
        if local_file.exists():
            try:
                return json.loads(local_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # 2. Try Firestore
        db = self.get_firestore()
        if db is not None:
            try:
                doc = db.collection("analyses").document(vid).get()
                if doc.exists:
                    raw_data = doc.to_dict() or {}
                    data = sanitize_json_dict(raw_data)
                    # Mirror to local disk cache for fast subsequent reads
                    local_file.parent.mkdir(parents=True, exist_ok=True)
                    local_file.write_text(safe_json_dumps(data, indent=2), encoding="utf-8")
                    return data
            except Exception as e:
                logger.warning(f"[StorageService] Failed fetching analysis from Firestore: {e}")

        # 3. Try GCS bucket
        bucket = self.get_storage_bucket()
        if bucket is not None:
            try:
                blob = bucket.blob(f"analyses/{vid}.json")
                if blob.exists():
                    raw = blob.download_as_text()
                    data = json.loads(raw)
                    local_file.parent.mkdir(parents=True, exist_ok=True)
                    local_file.write_text(raw, encoding="utf-8")
                    return data
            except Exception as e:
                logger.warning(f"[StorageService] Failed fetching analysis from GCS: {e}")

        return None

    def list_analyses(self) -> List[Dict[str, Any]]:
        """
        Lists summary metadata for all video analyses across local disk and Firestore.
        """
        items_by_id: Dict[str, Dict[str, Any]] = {}

        # 1. Fetch from Firestore
        db = self.get_firestore()
        if db is not None:
            try:
                docs = db.collection("analyses").stream()
                for doc in docs:
                    item = doc.to_dict() or {}
                    vid = item.get("video_id", doc.id)
                    items_by_id[vid] = {
                        "video_id": vid,
                        "title": item.get("title", "Analyzed Short"),
                        "channel": item.get("channel", "Creator"),
                        "duration_sec": item.get("duration_sec", 0),
                        "virality_score": item.get("virality_score", 0),
                        "views": item.get("engagement", {}).get("views", 0),
                        "likes": item.get("engagement", {}).get("likes", 0),
                        "engagement_rate": item.get("engagement", {}).get("engagement_rate", 0),
                        "style_tags": item.get("style_tags", []),
                        "shots_count": len(item.get("video_graph", {}).get("nodes", [])),
                    }
            except Exception as e:
                logger.warning(f"[StorageService] Failed listing analyses from Firestore: {e}")

        # 2. Merge local disk
        data_dir = BASE_DIR / "corpus" / "data"
        if data_dir.exists():
            for file_path in sorted(data_dir.glob("*.json")):
                if file_path.name in ("pattern_catalog.json", "director_context.json"):
                    continue
                vid = file_path.stem
                if vid not in items_by_id:
                    try:
                        item = json.loads(file_path.read_text(encoding="utf-8"))
                        items_by_id[vid] = {
                            "video_id": item.get("video_id", vid),
                            "title": item.get("title", "Analyzed Short"),
                            "channel": item.get("channel", "Creator"),
                            "duration_sec": item.get("duration_sec", 0),
                            "virality_score": item.get("virality_score", 0),
                            "views": item.get("engagement", {}).get("views", 0),
                            "likes": item.get("engagement", {}).get("likes", 0),
                            "engagement_rate": item.get("engagement", {}).get("engagement_rate", 0),
                            "style_tags": item.get("style_tags", []),
                            "shots_count": len(item.get("video_graph", {}).get("nodes", [])),
                        }
                    except Exception:
                        pass

        return list(items_by_id.values())

    # -------------------------------------------------------------------------
    # Creator Profile & DNA
    # -------------------------------------------------------------------------

    def save_creator_profile(
        self,
        session_id: Optional[str],
        profile_data: Dict[str, Any],
    ) -> None:
        """
        Persists Creator profile and synthesized DNA to Firestore.
        Firestore path: users/{session_id}/profile/creator_dna
        """
        safe_sess = self.sanitize_session_id(session_id)
        db = self.get_firestore()
        if db is not None:
            try:
                db.collection("users").document(safe_sess).collection("profile").document("creator_dna").set(
                    profile_data
                )
                logger.info(f"[StorageService] Creator profile saved to Firestore for '{safe_sess}'.")
            except Exception as e:
                logger.warning(f"[StorageService] Failed saving creator profile to Firestore: {e}")

    def get_creator_profile(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        safe_sess = self.sanitize_session_id(session_id)
        db = self.get_firestore()
        if db is not None:
            try:
                doc = (
                    db.collection("users")
                    .document(safe_sess)
                    .collection("profile")
                    .document("creator_dna")
                    .get()
                )
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.warning(f"[StorageService] Failed loading creator profile from Firestore: {e}")
        return None


# Global singleton instance
storage_service = StorageService()

