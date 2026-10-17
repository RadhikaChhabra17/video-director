from __future__ import annotations

import glob
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from tools.youtube_tool import extract_youtube_id

logger = logging.getLogger(__name__)


def extract_media_info(url_or_id: str) -> tuple[str, str, str]:
    """
    Returns (video_id, target_url, platform)
    Supports:
    - Local video files (.mp4, .mov, .webm, .mkv)
    - Instagram Reels (instagram.com/reel/..., instagram.com/p/...)
    - TikTok (tiktok.com/...)
    - YouTube Shorts / Videos
    """
    cleaned = url_or_id.strip()
    if os.path.isfile(cleaned):
        path = Path(cleaned)
        safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", path.stem)
        return safe_id, str(path.resolve()), "local"

    if "instagram.com" in cleaned or "instagr.am" in cleaned:
        ig_match = re.search(r"/(?:reel|reels|p)/([a-zA-Z0-9_-]+)", cleaned)
        shortcode = ig_match.group(1) if ig_match else "reel"
        return f"ig_{shortcode}", cleaned, "instagram_reels"

    if "tiktok.com" in cleaned:
        tt_match = re.search(r"/video/(\d+)", cleaned)
        tt_id = tt_match.group(1) if tt_match else "tiktok"
        return f"tt_{tt_id}", cleaned, "tiktok"

    yt_id = extract_youtube_id(cleaned)
    return yt_id, f"https://www.youtube.com/shorts/{yt_id}", "youtube_shorts"


def get_cached_video(video_id: str, cache_dir: str = ".cache/videos") -> Optional[str]:
    if not os.path.exists(cache_dir):
        return None

    for ext in ("mp4", "webm", "mkv", "mov"):
        candidate = os.path.join(cache_dir, f"{video_id}.{ext}")
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 10000:
            return os.path.abspath(candidate)

    matches = glob.glob(os.path.join(cache_dir, f"{video_id}.*"))
    for match in matches:
        if os.path.isfile(match) and os.path.getsize(match) > 10000:
            return os.path.abspath(match)

    return None


def get_ffmpeg_binary() -> Optional[str]:
    """Returns the path to the ffmpeg executable, checking system PATH then imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return None


def download_short_video(
    url_or_id: str,
    cache_dir: str = ".cache/videos",
    max_height: int = 720,
) -> str:
    cleaned = url_or_id.strip()
    if os.path.isfile(cleaned):
        return os.path.abspath(cleaned)

    video_id, target_url, platform = extract_media_info(cleaned)
    os.makedirs(cache_dir, exist_ok=True)

    cached = get_cached_video(video_id, cache_dir)
    if cached:
        logger.info("Using cached video for %s %s: %s", platform, video_id, cached)
        return cached

    import yt_dlp

    short_url = target_url
    out_template = os.path.join(cache_dir, f"{video_id}.%(ext)s")
    ffmpeg_exe = get_ffmpeg_binary()
    has_ffmpeg = ffmpeg_exe is not None

    extractor_args = {
        "youtube": {
            "player_client": ["android", "ios", "web"],
        }
    }

    if has_ffmpeg:
        format_selector = (
            f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={max_height}]+bestaudio/"
            "bestvideo+bestaudio/best"
        )
        ydl_opts = {
            "format": format_selector,
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "overwrites": True,
            "extractor_args": extractor_args,
        }
    else:
        format_selector = (
            f"best[height<={max_height}][vcodec!=none][acodec!=none]/"
            f"best[vcodec!=none][acodec!=none]/"
            f"bestvideo[height<={max_height}][ext=mp4]/"
            "best"
        )
        ydl_opts = {
            "format": format_selector,
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "overwrites": True,
            "extractor_args": extractor_args,
        }

    if ffmpeg_exe:
        ydl_opts["ffmpeg_location"] = ffmpeg_exe

    cookies_path = os.getenv("YOUTUBE_COOKIES_PATH", "cookies.txt")
    if os.path.isfile(cookies_path):
        ydl_opts["cookiefile"] = cookies_path

    logger.info("Downloading video stream for Short %s (%s)...", video_id, short_url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([short_url])

    downloaded = get_cached_video(video_id, cache_dir)
    if not downloaded or not os.path.exists(downloaded):
        raise RuntimeError(
            f"Failed to locate downloaded video for '{video_id}' in '{cache_dir}'"
        )

    logger.info("Video successfully saved at %s", downloaded)
    return downloaded


def has_audio_stream(file_path: str) -> bool:
    """Returns True if the media file contains at least one audio stream."""
    import subprocess
    ffmpeg_exe = get_ffmpeg_binary()
    if not ffmpeg_exe or not os.path.isfile(file_path):
        return False
    cmd = [ffmpeg_exe, "-i", file_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return "Audio:" in res.stderr


def download_short_audio(
    url_or_path: str,
    output_dir: str = "audio_exports",
    audio_format: str = "mp3",
) -> str:
    """
    Extracts or downloads audio track from an Instagram Reel, YouTube Short, or local video file.
    Returns the absolute path to the extracted audio file.
    """
    import subprocess
    os.makedirs(output_dir, exist_ok=True)
    video_id, target_url, platform = extract_media_info(url_or_path)

    expected_path = os.path.join(output_dir, f"{video_id}.{audio_format}")
    if os.path.isfile(expected_path) and os.path.getsize(expected_path) > 1000:
        return os.path.abspath(expected_path)

    # 1. Obtain local video file (from cache, local disk, or download)
    video_file = None
    if os.path.isfile(url_or_path.strip()):
        video_file = os.path.abspath(url_or_path.strip())
    else:
        cached = get_cached_video(video_id)
        if cached and os.path.isfile(cached) and has_audio_stream(cached):
            video_file = cached
        else:
            try:
                # Remove stale audio-less cache if present
                if cached and os.path.isfile(cached):
                    try:
                        os.remove(cached)
                    except OSError:
                        pass
                video_file = download_short_video(url_or_path)
            except Exception as e:
                logger.warning("Failed to download full video for %s: %s", url_or_path, e)

    # 2. If video file is available, extract audio directly via ffmpeg
    ffmpeg_exe = get_ffmpeg_binary()
    if video_file and os.path.isfile(video_file) and ffmpeg_exe:
        logger.info("Extracting audio from %s using ffmpeg...", video_file)
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(video_file),
            "-vn",
        ]
        fmt_lower = audio_format.lower()
        if fmt_lower == "mp3":
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"])
        elif fmt_lower in ("m4a", "aac"):
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        elif fmt_lower == "wav":
            cmd.extend(["-c:a", "pcm_s16le"])
        else:
            cmd.extend(["-c:a", "copy"])
        cmd.append(expected_path)

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.isfile(expected_path) and os.path.getsize(expected_path) > 1000:
            return os.path.abspath(expected_path)
        logger.warning("ffmpeg audio extraction failed (code %d): %s", res.returncode, res.stderr[:200])

    # 3. Fallback: direct yt-dlp audio download from target_url
    import yt_dlp
    out_template = os.path.join(output_dir, f"{video_id}.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "overwrites": True,
    }
    if ffmpeg_exe:
        ydl_opts["ffmpeg_location"] = ffmpeg_exe

    cookies_path = os.getenv("YOUTUBE_COOKIES_PATH", "cookies.txt")
    if os.path.isfile(cookies_path):
        ydl_opts["cookiefile"] = cookies_path

    logger.info("Extracting audio from %s (%s) via yt-dlp...", platform, target_url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([target_url])

    if os.path.exists(expected_path):
        return os.path.abspath(expected_path)

    for f in glob.glob(os.path.join(output_dir, f"{video_id}.*")):
        if os.path.isfile(f) and os.path.getsize(f) > 1000:
            return os.path.abspath(f)

    raise RuntimeError(f"Audio extraction failed for {url_or_path}")
