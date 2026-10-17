from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import yt_dlp

logger = logging.getLogger(__name__)


def extract_youtube_id(url_or_id: str) -> str:
    cleaned = url_or_id.strip()

    shorts_match = re.search(r"/(?:shorts)/([a-zA-Z0-9_-]{11})", cleaned)
    if shorts_match:
        return shorts_match.group(1)

    watch_match = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", cleaned)
    if watch_match:
        return watch_match.group(1)

    shortlink_match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", cleaned)
    if shortlink_match:
        return shortlink_match.group(1)

    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", cleaned):
        return cleaned

    generic_match = re.search(r"([a-zA-Z0-9_-]{11})", cleaned)
    if generic_match:
        return generic_match.group(1)

    return cleaned


def fetch_youtube_metadata(
    url_or_id: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    video_id = extract_youtube_id(url_or_id)
    canonical_url = f"https://www.youtube.com/shorts/{video_id}"

    resolved_key = api_key or os.getenv("YOUTUBE_API_KEY")

    if resolved_key:
        try:
            return _fetch_via_youtube_api(video_id, canonical_url, resolved_key)
        except Exception as e:
            logger.warning(
                "YouTube Data API failed for %s (%s). Falling back to yt-dlp.",
                video_id,
                e,
            )

    return _fetch_via_ytdlp(video_id, canonical_url)


def _fetch_via_youtube_api(
    video_id: str, canonical_url: str, api_key: str
) -> dict[str, Any]:
    endpoint = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?id={video_id}&part=snippet,contentDetails,statistics&key={api_key}"
    )

    req = urllib.request.Request(endpoint, headers={"User-Agent": "ContentCreation-Agent/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    items = data.get("items", [])
    if not items:
        raise ValueError(f"Video ID '{video_id}' not found via YouTube API.")

    item = items[0]
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})
    content_details = item.get("contentDetails", {})

    iso_dur = content_details.get("duration", "PT0S")
    duration_sec = _parse_iso_duration(iso_dur)

    views = int(statistics.get("viewCount", 0))
    likes = int(statistics.get("likeCount", 0))
    comments = int(statistics.get("commentCount", 0))

    engagement_rate = (
        round(((likes + comments) / views) * 100, 2) if views > 0 else 0.0
    )

    raw_date = snippet.get("publishedAt")
    if raw_date:
        posted_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    else:
        posted_at = datetime.now(timezone.utc)

    return {
        "video_id": video_id,
        "url": canonical_url,
        "title": snippet.get("title", ""),
        "channel": snippet.get("channelTitle", ""),
        "platform": "youtube_shorts",
        "category": snippet.get("categoryId", "General"),
        "duration_sec": max(duration_sec, 1.0),
        "posted_at": posted_at,
        "aspect_ratio": "9:16",
        "fps": 30.0,
        "views": views,
        "likes": likes,
        "comments": comments,
        "engagement_rate": engagement_rate,
    }


def _fetch_via_ytdlp(video_id: str, canonical_url: str) -> dict[str, Any]:
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(canonical_url, download=False)
        except Exception:
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            info = ydl.extract_info(watch_url, download=False)

    if not info:
        raise ValueError(f"Failed to extract info for video ID: {video_id}")

    views = int(info.get("view_count") or 0)
    likes = int(info.get("like_count") or 0)
    comments = int(info.get("comment_count") or 0)

    engagement_rate = (
        round(((likes + comments) / views) * 100, 2) if views > 0 else 0.0
    )

    duration_sec = float(info.get("duration") or 0.0)

    upload_date = info.get("upload_date")
    if upload_date and len(upload_date) == 8:
        posted_at = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
    else:
        posted_at = datetime.now(timezone.utc)

    width = info.get("width")
    height = info.get("height")
    if width and height:
        aspect_ratio = f"{width}:{height}" if height > width else "9:16"
    else:
        aspect_ratio = "9:16"

    fps = float(info.get("fps") or 30.0)

    return {
        "video_id": video_id,
        "url": canonical_url,
        "title": info.get("title", ""),
        "channel": info.get("channel") or info.get("uploader", ""),
        "platform": "youtube_shorts",
        "category": (info.get("categories") or ["General"])[0],
        "duration_sec": max(duration_sec, 1.0),
        "posted_at": posted_at,
        "aspect_ratio": aspect_ratio,
        "fps": fps,
        "views": views,
        "likes": likes,
        "comments": comments,
        "engagement_rate": engagement_rate,
    }


def fetch_youtube_captions(video_id: str, timeout: int = 5) -> list[dict[str, Any]]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
        if not match:
            return []

        player_data = json.loads(match.group(1))
        captions_obj = player_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {})
        tracks = captions_obj.get("captionTracks", [])
        if not tracks:
            return []

        target_track = next((t for t in tracks if t.get("languageCode", "").startswith("en")), tracks[0])
        base_url = target_track.get("baseUrl")
        if not base_url:
            return []

        sub_req = urllib.request.Request(base_url, headers=headers)
        with urllib.request.urlopen(sub_req, timeout=timeout) as sub_resp:
            xml_data = sub_resp.read().decode("utf-8", errors="ignore")

        root = ET.fromstring(xml_data)

        entries = []
        for text_elem in root.findall(".//text"):
            start = float(text_elem.get("start", "0.0"))
            dur = float(text_elem.get("dur", "0.0"))
            txt = (text_elem.text or "").replace("&#39;", "'").replace("&quot;", '"').strip()
            if txt:
                entries.append({
                    "start": round(start, 2),
                    "duration": round(dur, 2),
                    "end": round(start + dur, 2),
                    "text": txt,
                })
        return entries
    except Exception as e:
        logger.debug("Caption extraction skipped for %s: %s", video_id, e)
        return []


def _parse_iso_duration(duration_str: str) -> float:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", duration_str)
    if not match:
        return 0.0
    hours = float(match.group(1) or 0)
    minutes = float(match.group(2) or 0)
    seconds = float(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds
