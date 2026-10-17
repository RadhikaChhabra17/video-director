from __future__ import annotations

import logging
import os
import time
from typing import Optional

from pydantic import BaseModel, Field

from corpus.schema import GraphNode

logger = logging.getLogger(__name__)


class ShotPerceptionOutput(BaseModel):
    shots: list[GraphNode] = Field(
        ...,
        description="Sequential list of dynamic per-shot nodes spanning the full video duration",
    )


SHOT_ANALYSIS_PROMPT = """You are an expert short-form video director, cinematic colorist, and retention editor.
Analyze this video at the GRANULAR, INDIVIDUAL SHOT level.

CRITICAL RULES ON SHOT GRANULARITY & PACING:
1. In high-retention short-form video (YouTube Shorts, TikTok, Reels), the visual changes every 1.0 to 2.5 seconds.
2. NEVER group a long 15s, 30s, or 60s section into a single shot!
3. Every camera switch, B-roll insert, punch-in (snap zoom), jump cut, or angle change is a distinct SHOT (node).
4. Shots MUST be contiguous and non-overlapping: shot[i].timestamp_range.end_sec == shot[i+1].timestamp_range.start_sec.
5. Set rel_position = start_sec / total_duration (normalized between 0.0 and 1.0).

FOR EVERY SHOT NODE:
- event_id: "shot_01", "shot_02", "shot_03", etc.
- beat_name: HOOK, CONTEXT, PROBLEM, DEMO, TWIST, PROOF, PAYOFF, CTA.
- hook_type: Choose from defined HookType enum (e.g. CURIOSITY, QUESTION, CONTRARIAN, VISUAL_ACTION, PATTERN_INTERRUPT, etc.).
- timestamp_range: start_sec and end_sec.
- description: Concise summary of what is visually and narratively happening in this shot.
- transcript: Words spoken by speaker/voiceover during this specific shot.
- ocr_text: Any on-screen text, subtitles, or captions visually rendered on the screen.
- camera: shot_size (ecu, cu, mcu, m, mw, w, ew) and movement (static, pan, tilt, zoom, handheld, tracking, whip, dolly, etc.).
- speaker_telemetry: is_speaking, on_camera, face_expression (e.g. smirking, deadpan, shocked, smiling), action (physical gesture or movement), wpm, energy_level, vocal_delivery (conversational, excited, deadpan, urgent, etc.).
- audio_style: has_voiceover, has_background_music, music_mood, sfx_tags (e.g. ["whoosh", "boom"]), audio_energy.
- video_style: visual_format (talking_head, b_roll, screen_recording, skit), lighting, text_overlay_type, visual_effects, visual_density.
- interpretation_confidence: LOW, MEDIUM, or HIGH.
"""


def analyze_shots_multimodal(
    video_path: str,
    title: str = "",
    duration_sec: float = 0.0,
    transcript_text: str = "",
    api_key: str | None = None,
    model_name: str = "gemini-3.8-flash",
    cleanup_remote_file: bool = True,
) -> list[GraphNode]:
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("true", "1")
    resolved_key = (
        api_key
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("YOUTUBE_API_KEY")
    )
    if not resolved_key and not use_vertex:
        raise ValueError(
            "GEMINI_API_KEY or Vertex AI (GOOGLE_GENAI_USE_VERTEXAI=true) must be provided for Gemini multimodal processing."
        )

    from google import genai
    from google.genai import types
    from tools.pattern_tools import get_genai_client

    client = get_genai_client(api_key=resolved_key)

    file_size = os.path.getsize(video_path)
    logger.info("Video file size: %.2f MB for: %s", file_size / (1024 * 1024), video_path)

    mime_type = "video/mp4"
    if video_path.lower().endswith(".mov"):
        mime_type = "video/quicktime"
    elif video_path.lower().endswith(".webm"):
        mime_type = "video/webm"

    video_content = None
    uploaded_file = None
    gcs_blob = None
    dev_client = None

    # Strategy 1: For short-form videos <= 25MB, pass inline bytes directly.
    # Supported seamlessly on BOTH Vertex AI and Gemini Developer API without File API / client.files.
    if file_size <= 25 * 1024 * 1024:
        logger.info("Processing video via native inline bytes (%s)...", mime_type)
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        try:
            video_content = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        except Exception:
            video_content = types.Part(inline_data=types.Blob(data=video_bytes, mime_type=mime_type))

    # Strategy 2: For larger files on Vertex AI, upload to Google Cloud Storage
    elif use_vertex:
        try:
            from tools.storage_service import StorageService
            storage_svc = StorageService()
            bucket = storage_svc.get_storage_bucket()
            if bucket:
                import uuid
                from pathlib import Path
                blob_name = f"multimodal_uploads/{uuid.uuid4().hex[:8]}_{Path(video_path).name}"
                gcs_blob = bucket.blob(blob_name)
                logger.info("Uploading video to GCS bucket gs://%s/%s...", bucket.name, blob_name)
                gcs_blob.upload_from_filename(video_path, content_type=mime_type)
                gcs_uri = f"gs://{bucket.name}/{blob_name}"
                video_content = types.Part.from_uri(file_uri=gcs_uri, mime_type=mime_type)
        except Exception as e:
            logger.warning("GCS upload failed: %s. Falling back to inline bytes...", e)

    # Strategy 3: If still not set and resolved_key is present, use Gemini Developer Client (vertexai=False)
    if video_content is None and resolved_key:
        try:
            logger.info("Uploading video to Gemini Developer File API with API key...")
            dev_client = genai.Client(api_key=resolved_key, vertexai=False)
            uploaded_file = dev_client.files.upload(file=video_path)
            logger.info("Uploaded file ID: %s. Awaiting processing...", uploaded_file.name)
            poll_count = 0
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(2)
                poll_count += 1
                uploaded_file = dev_client.files.get(name=uploaded_file.name)
                if poll_count > 60:
                    raise TimeoutError("Gemini video file processing timed out after 120s.")
            if uploaded_file.state.name == "FAILED":
                raise RuntimeError(f"Gemini video processing failed: {uploaded_file.error}")
            video_content = uploaded_file
        except Exception as e:
            logger.warning("Gemini Developer File API failed: %s. Falling back to inline bytes...", e)

    # Final Fallback: Read inline bytes up to 100MB
    if video_content is None:
        logger.info("Reading video bytes directly for inference...")
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        try:
            video_content = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        except Exception:
            video_content = types.Part(inline_data=types.Blob(data=video_bytes, mime_type=mime_type))

    try:
        logger.info("Video ready for inference. Running multimodal perception with %s...", model_name)

        prompt_content = f"{SHOT_ANALYSIS_PROMPT}\n\nVIDEO TITLE: {title}\nTOTAL DURATION: {duration_sec:.1f}s"
        if transcript_text:
            prompt_content += f"\n\nTRANSCRIPT CONTEXT:\n{transcript_text}"

        models_to_try = [model_name]
        for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
            if m not in models_to_try:
                models_to_try.append(m)

        response = None
        last_error = None

        for target_model in models_to_try:
            for attempt in range(1, 4):
                try:
                    logger.info("Attempt %d/3 calling %s...", attempt, target_model)
                    response = client.models.generate_content(
                        model=target_model,
                        contents=[video_content, prompt_content],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ShotPerceptionOutput,
                            temperature=0.2,
                        ),
                    )
                    if response and response.text:
                        break
                except Exception as e:
                    last_error = e
                    err_msg = str(e)
                    if ("503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg) and attempt < 3:
                        logger.warning(
                            "Transient model error on %s (attempt %d/3): %s. Backing off...",
                            target_model,
                            attempt,
                            err_msg,
                        )
                        time.sleep(attempt * 4)
                        continue
                    logger.warning("Model %s failed attempt %d: %s. Trying next candidate model...", target_model, attempt, e)
                    break
            if response and response.text:
                break

        if not response or not response.text:
            raise RuntimeError(f"All multimodal inference attempts failed. Last error: {last_error}")

        output_data = ShotPerceptionOutput.model_validate_json(response.text)
        shots = output_data.shots

        shots.sort(key=lambda s: s.timestamp_range.start_sec)

        total_dur = max(duration_sec, shots[-1].timestamp_range.end_sec if shots else 1.0)
        for idx, shot in enumerate(shots, start=1):
            if not shot.event_id or shot.event_id == "shot":
                shot.event_id = f"shot_{idx:02d}"
            shot.rel_position = round(shot.timestamp_range.start_sec / total_dur, 3)

        logger.info("Perception complete: extracted %d dynamic shot nodes.", len(shots))
        return shots

    finally:
        if cleanup_remote_file:
            if uploaded_file and dev_client:
                try:
                    dev_client.files.delete(name=uploaded_file.name)
                    logger.debug("Cleaned up remote file: %s", uploaded_file.name)
                except Exception as e:
                    logger.debug("Remote file cleanup note: %s", e)
            if gcs_blob:
                try:
                    gcs_blob.delete()
                    logger.debug("Cleaned up GCS blob: %s", gcs_blob.name)
                except Exception as e:
                    logger.debug("GCS blob cleanup note: %s", e)
