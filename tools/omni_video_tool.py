from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import errors, types

from corpus.director_schema import DirectorResponseManifest


def get_ffmpeg_binary() -> str:
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return "ffmpeg"


def sanitize_error(err: Any) -> str:
    if not err:
        return ""
    if isinstance(err, errors.APIError):
        parts: List[str] = []
        if getattr(err, "code", None):
            parts.append(str(err.code))
        if getattr(err, "status", None):
            parts.append(f"({err.status})")
        if getattr(err, "message", None):
            parts.append(f": {err.message}")
        elif getattr(err, "details", None):
            parts.append(f": {err.details}")
        err_str = " ".join(parts) if parts else str(err)
    else:
        err_str = str(err)

    key = os.environ.get("GEMINI_API_KEY", "")
    if key and len(key) >= 8:
        err_str = err_str.replace(key, "[REDACTED_KEY]")

    err_str = re.sub(r"AIza[0-9A-Za-z_\-]{30,}", "[REDACTED_KEY]", err_str)
    err_str = re.sub(r"AQ\.[0-9A-Za-z_\-]{20,}", "[REDACTED_KEY]", err_str)
    err_str = re.sub(r"ya29\.[0-9A-Za-z_\-]+", "[REDACTED_TOKEN]", err_str)
    err_str = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED_TOKEN]", err_str, flags=re.IGNORECASE)
    err_str = re.sub(r"([?&](?:key|api_key|apiKey|access_token|auth|signature)=)[^&\s\"'<>()]+", r"\1[REDACTED]", err_str)
    err_str = re.sub(r"\s+", " ", err_str).strip()
    return err_str[:400]


def format_srt_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def burn_captions_to_video(
    video_path: str,
    manifest: DirectorResponseManifest,
    output_path: Optional[str] = None,
    total_video_duration: Optional[float] = 8.0,
) -> str:
    """Burns on-screen kinetic captions (subtitles/OCR) into video using FFmpeg."""
    if not manifest.shots or not os.path.exists(video_path):
        return video_path

    manifest_total = sum(s.duration_sec for s in manifest.shots if s.duration_sec) or 8.0
    scale = (total_video_duration / manifest_total) if total_video_duration else 1.0

    cues = []
    current_time = 0.0
    for i, shot in enumerate(manifest.shots, 1):
        dur = shot.duration_sec * scale
        cap_text = ""
        if shot.overlays and shot.overlays.captions and shot.overlays.captions.text:
            cap_text = shot.overlays.captions.text.strip()
        elif shot.audio and shot.audio.speech and shot.audio.speech.transcript:
            cap_text = shot.audio.speech.transcript.strip()

        if cap_text:
            cues.append({
                "index": i,
                "start": current_time,
                "end": current_time + max(dur, 0.8),
                "text": cap_text,
            })
        current_time += dur

    if not cues:
        return video_path

    with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as srt_f:
        srt_path = srt_f.name
        for item in cues:
            srt_f.write(f"{item['index']}\n")
            srt_f.write(f"{format_srt_time(item['start'])} --> {format_srt_time(item['end'])}\n")
            srt_f.write(f"{item['text']}\n\n")

    target_out = output_path or video_path.replace(".mp4", "_captioned.mp4")
    bin_path = get_ffmpeg_binary()

    try:
        safe_srt = srt_path.replace("\\", "/").replace(":", "\\:")
        cmd = [
            bin_path,
            "-y",
            "-i", video_path,
            "-vf", f"subtitles={safe_srt}:force_style='Fontsize=22,Fontname=Arial,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=65'",
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            target_out,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0 and os.path.exists(target_out) and os.path.getsize(target_out) > 1000:
            print(f"[CAPTIONS] Burned on-screen captions successfully to: {target_out}")
            if output_path is None:
                os.replace(target_out, video_path)
                return video_path
            return target_out
        else:
            print(f"[WARN] FFmpeg caption burn skipped: {sanitize_error(proc.stderr)}")
            return video_path
    except Exception as e:
        print(f"[WARN] Caption burn exception: {sanitize_error(e)}")
        return video_path
    finally:
        if os.path.exists(srt_path):
            os.remove(srt_path)


def construct_master_8s_prompt(manifest: DirectorResponseManifest) -> str:
    parts: List[str] = []

    # 1. Title & Concept Premise
    if manifest.concept_summary:
        parts.append(manifest.concept_summary.strip())
    elif manifest.title:
        parts.append(f"{manifest.title}.")

    # 2. Sequential narrative arc across shots
    actions = [s.visual.subject_action.strip() for s in manifest.shots if s.visual and s.visual.subject_action]
    if actions:
        if len(actions) == 1:
            parts.append(f"Action: {actions[0]}")
        else:
            flow_str = " -> ".join(actions[:3])
            parts.append(f"Visual flow: {flow_str}.")

    # 3. Framing & Camera
    camera_styles = [s.visual.camera_movement.value for s in manifest.shots if s.visual and s.visual.camera_movement]
    cam_str = camera_styles[0] if camera_styles else "dynamic cinematic push-in"
    parts.append(f"Camera movement: smooth continuous {cam_str}.")

    # 4. Spoken Dialogue from the shots
    dialogues: List[str] = []
    for s in manifest.shots:
        if s.audio and s.audio.speech and s.audio.speech.transcript:
            t = s.audio.speech.transcript.strip()
            if t and t not in dialogues:
                dialogues.append(t)
    if dialogues:
        combined_dialogue = " ".join(dialogues[:2])
        parts.append(f'Spoken dialogue: The subject speaks with clear, natural delivery: "{combined_dialogue}".')

    # 5. Lighting & Visual Style
    if manifest.visual_style_anchor:
        parts.append(f"Visual style: {manifest.visual_style_anchor.strip()}.")
    elif manifest.shots and manifest.shots[0].visual.lighting:
        parts.append(f"Lighting: {manifest.shots[0].visual.lighting.strip()}.")

    # 6. Audio Design & SFX
    sfx_items: List[str] = []
    for s in manifest.shots:
        if s.audio and s.audio.sfx_cues:
            sfx_items.extend([cue.sfx_name for cue in s.audio.sfx_cues if cue.sfx_name])
    if sfx_items:
        unique_sfx = list(dict.fromkeys(sfx_items))[:3]
        parts.append(f"Audio design: realistic atmospheric audio with sound effects including {', '.join(unique_sfx)}.")
    else:
        parts.append("Audio design: rich natural room acoustics, clear vocal audio, and immersive atmospheric sound.")

    # 7. Directing constraint
    parts.append("Single continuous 10-second cinematic shot, seamless motion, pristine 9:16 vertical composition, photorealistic textures, no scene cuts.")
    return " ".join(parts)


def get_gcp_access_token() -> Optional[str]:
    """Retrieves GCP OAuth access token via environment, gcloud CLI, or google.auth."""
    tok = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
    if tok:
        return tok.strip()
    try:
        proc = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True, check=True)
        tok = proc.stdout.strip()
        if tok:
            return tok
    except Exception:
        pass
    try:
        import google.auth
        import google.auth.transport.requests
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        return creds.token
    except Exception:
        pass
    return None


def extract_video_bytes_from_response(data: Any) -> bytes:
    """Recursively traverses API response JSON to extract MP4 bytes from base64 data or download URI."""
    import base64

    if isinstance(data, dict):
        if data.get("mime_type") == "video/mp4" or data.get("type") == "video":
            for k in ["data", "bytes", "b64", "content"]:
                if k in data and isinstance(data[k], str) and len(data[k]) > 100:
                    return base64.b64decode(data[k])
            if "uri" in data and isinstance(data["uri"], str):
                uri = data["uri"]
                if uri.startswith("gs://"):
                    from google.cloud import storage
                    parts = uri[5:].split("/", 1)
                    client = storage.Client()
                    return client.bucket(parts[0]).blob(parts[1]).download_as_bytes()
                else:
                    import urllib.request
                    with urllib.request.urlopen(uri) as r:
                        return r.read()

        for k in ["data", "bytes"]:
            if k in data and isinstance(data[k], str) and len(data[k]) > 500:
                try:
                    return base64.b64decode(data[k])
                except Exception:
                    pass

        for v in data.values():
            try:
                b = extract_video_bytes_from_response(v)
                if b:
                    return b
            except Exception:
                pass

    elif isinstance(data, list):
        for item in data:
            try:
                b = extract_video_bytes_from_response(item)
                if b:
                    return b
            except Exception:
                pass

    raise RuntimeError("Could not find video data or download URI in Omni API response.")


def generate_master_8s_video(
    manifest: DirectorResponseManifest,
    output_path: str,
    aspect_ratio: str = "9:16",
    resolution: str = "720p",
    model: str = "gemini-omni-1.1-flash-preview",
    timeout_s: int = 600,
    client: Optional[genai.Client] = None,
    first_frame_path: Optional[str] = None,
) -> str:
    """Generates a 10-second master reference video using Gemini Omni 1.1 Flash via Interactions API."""
    import base64
    import json
    import urllib.request
    import urllib.error

    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("true", "1")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get("GEMINI_API_KEY")
        except Exception:
            pass

    ar = "9:16" if ("9:16" in aspect_ratio or "9/16" in aspect_ratio) else "16:9"
    res = "1080p" if "1080" in resolution else "720p"

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "aibuildercup2026")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("GEMINI_LOCATION") or "global"

    prompt_text = construct_master_8s_prompt(manifest)

    input_parts: List[Dict[str, Any]] = []

    # Optional initial reference frame
    if first_frame_path and os.path.exists(first_frame_path):
        try:
            with open(first_frame_path, "rb") as f:
                img_bytes = f.read()
            ext = Path(first_frame_path).suffix.lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            input_parts.append({
                "type": "image",
                "data": base64.b64encode(img_bytes).decode("utf-8"),
                "mime_type": mime,
            })
        except Exception as e:
            print(f"[WARN] Failed to load initial frame for Omni: {sanitize_error(e)}")

    # Main text prompt
    input_parts.append({
        "type": "text",
        "text": prompt_text,
    })

    # Model resolution: try requested model, then standard Omni fallbacks
    candidates = [model]
    if use_vertex:
        candidates.extend([
            "gemini-omni-1.1-flash-preview",
            "gemini-omni-1.1-flash",
        ])
    else:
        candidates.extend([
            "gemini-omni-1.1-flash",
            "gemini-omni-1.1-flash-preview",
        ])
    seen = set()
    model_candidates = [m for m in candidates if not (m in seen or seen.add(m))]

    token = get_gcp_access_token() if use_vertex or not api_key else None

    # Determine endpoint
    if use_vertex or (token and not api_key):
        endpoint_url = f"https://aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{location}/interactions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
    else:
        if not api_key:
            raise RuntimeError("Neither GCP Vertex AI credentials nor GEMINI_API_KEY is configured for video generation.")
        endpoint_url = f"https://generativelanguage.googleapis.com/v1beta/interactions?key={api_key}"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }

    last_err: Optional[Exception] = None
    response_json: Optional[Dict[str, Any]] = None

    for candidate_model in model_candidates:
        print(f"[OMNI MASTER 8S] Submitting generation (model: {candidate_model}, aspect: {ar}, res: {res})...")
        print(f"[OMNI MASTER 8S] Prompt: \"{prompt_text[:120]}...\"")

        payload = {
            "model": candidate_model,
            "input": input_parts,
            "response_format": {
                "type": "video",
                "aspect_ratio": ar,
            },
        }

        req = urllib.request.Request(
            endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                resp_bytes = resp.read()
                response_json = json.loads(resp_bytes.decode("utf-8"))
                break
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="ignore")
            print(f"[WARN] Candidate model '{candidate_model}' HTTP error {he.code}: {err_body[:300]}")
            last_err = RuntimeError(f"HTTP {he.code}: {err_body}")
            if he.code == 404 or "not supported" in err_body.lower():
                continue
            raise last_err
        except Exception as e:
            last_err = e
            print(f"[WARN] Candidate model '{candidate_model}' failed: {sanitize_error(e)}")
            continue

    if response_json is None:
        raise RuntimeError(f"Gemini Omni video generation failed: {sanitize_error(last_err)}")

    # Extract MP4 video bytes from Omni response
    video_bytes = extract_video_bytes_from_response(response_json)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(video_bytes)

    size_mb = len(video_bytes) / (1024 * 1024)
    print(f"[OMNI MASTER 10S] Saved raw video ({size_mb:.2f} MB) to: {output_path}")

    # Burn kinetic subtitles onto generated video
    return burn_captions_to_video(output_path, manifest, total_video_duration=10.0)


# Aliases for 10-second reference generation
construct_master_10s_prompt = construct_master_8s_prompt
generate_master_10s_video = generate_master_8s_video
