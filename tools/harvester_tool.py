from __future__ import annotations

import json
import logging
import math
import os
import statistics
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yt_dlp

from agents.shorts_agent import ShortsIntelligenceAgent
from tools.youtube_tool import _parse_iso_duration, extract_youtube_id

logger = logging.getLogger("HarvesterTool")


class SilentYtdlLogger:
    def debug(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        pass


def parse_published_datetime(date_val: Any) -> datetime | None:
    if not date_val:
        return None
    if isinstance(date_val, (int, float)):
        try:
            return datetime.fromtimestamp(date_val, tz=timezone.utc)
        except Exception:
            return None
    s = str(date_val).strip()
    if not s:
        return None
    try:
        if len(s) == 8 and s.isdigit():
            return datetime.strptime(s, "%Y%m%d").replace(tzinfo=timezone.utc)
        clean_s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_s)
    except Exception:
        return None


def is_within_days(published_at_str: str | None, max_days: int | None) -> bool:
    if not max_days or max_days <= 0:
        return True
    if not published_at_str:
        return True
    dt = parse_published_datetime(published_at_str)
    if not dt:
        return True
    now = datetime.now(timezone.utc)
    diff_seconds = (now - dt).total_seconds()
    age_days = diff_seconds / 86400.0
    return -1.0 <= age_days <= float(max_days)


def parse_timeline_days(val: str | int | None) -> int | None:
    if val is None:
        return None
    if isinstance(val, int):
        return val if val > 0 else None
    s = str(val).strip().lower()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s.endswith("d") and s[:-1].isdigit():
        return int(s[:-1])
    if s.endswith("w") and s[:-1].isdigit():
        return int(s[:-1]) * 7
    if s.endswith("m") and s[:-1].isdigit():
        return int(s[:-1]) * 30
    if s.endswith("mo") and s[:-2].isdigit():
        return int(s[:-2]) * 30
    if "month" in s:
        parts = s.split("month")[0].strip()
        num = int(parts) if parts.isdigit() else 1
        return num * 30
    if "week" in s:
        parts = s.split("week")[0].strip()
        num = int(parts) if parts.isdigit() else 1
        return num * 7
    if "day" in s:
        parts = s.split("day")[0].strip()
        num = int(parts) if parts.isdigit() else 1
        return num
    try:
        return int(s)
    except ValueError:
        return None


def get_existing_analyzed_ids(data_dir: str | Path = "corpus/data") -> set[str]:
    path = Path(data_dir)
    if not path.exists():
        return set()
    return {
        f.stem
        for f in path.glob("*.json")
        if f.is_file() and f.stem not in ("pattern_catalog", "director_context")
    }


def is_already_analyzed(video_id: str, data_dir: str | Path = "corpus/data") -> bool:
    return (Path(data_dir) / f"{video_id}.json").exists()


def load_creators_registry(
    registry_path: str | Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    candidates = []
    if registry_path:
        candidates.append(Path(registry_path))
    candidates.append(Path("corpus/creators_registry.json"))
    candidates.append(Path(__file__).resolve().parent.parent / "corpus" / "creators_registry.json")

    for path in candidates:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            return json.loads(content)

    return {}


def normalize_channel_url(channel_input: str) -> str:
    cleaned = channel_input.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        base_url = cleaned.rstrip("/")
        if not base_url.endswith("/shorts"):
            return f"{base_url}/shorts"
        return base_url

    if not cleaned.startswith("@"):
        cleaned = f"@{cleaned}"

    return f"https://www.youtube.com/{cleaned}/shorts"


def fetch_channel_shorts_urls(
    channel_handle_or_url: str,
    limit: int = 30,
) -> list[str]:
    target_url = normalize_channel_url(channel_handle_or_url)
    logger.info("Fetching top %d shorts from %s...", limit, target_url)

    ydl_opts: dict[str, Any] = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "logger": SilentYtdlLogger(),
        "playlistend": limit * 2,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        },
    }

    shorts_urls: list[str] = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            res = ydl.extract_info(target_url, download=False)
            entries = res.get("entries", []) if res else []
            for entry in entries:
                if not entry:
                    continue
                v_id = entry.get("id")
                dur = entry.get("duration")
                if dur is not None and (dur < 15 or dur > 70):
                    continue
                if v_id and len(v_id) == 11:
                    shorts_urls.append(f"https://www.youtube.com/shorts/{v_id}")
                if len(shorts_urls) >= limit:
                    break
        except Exception as e:
            logger.debug("Flat extraction failed for %s: %s", target_url, e)

    return shorts_urls


def fetch_channel_shorts_metadata(
    channel_handle_or_url: str,
    limit: int = 30,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    urls = fetch_channel_shorts_urls(channel_handle_or_url, limit=limit)
    if not urls:
        return []

    video_ids = [extract_youtube_id(u) for u in urls]
    resolved_key = api_key or os.getenv("YOUTUBE_API_KEY")

    if resolved_key:
        try:
            return _fetch_batch_metadata_api(video_ids, resolved_key)
        except Exception as e:
            logger.warning("Batch API fetch failed for %s (%s). Falling back.", channel_handle_or_url, e)

    results: list[dict[str, Any]] = []
    for vid in video_ids:
        try:
            meta = _fetch_single_metadata_ytdlp(vid)
            results.append(meta)
        except Exception:
            continue
    return results


def _fetch_batch_metadata_api(video_ids: list[str], api_key: str) -> list[dict[str, Any]]:
    unique_ids = list(dict.fromkeys(video_ids))
    results: list[dict[str, Any]] = []
    chunk_size = 50

    for i in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[i : i + chunk_size]
        ids_param = ",".join(chunk)
        url = (
            f"https://www.googleapis.com/youtube/v3/videos"
            f"?id={ids_param}&part=snippet,contentDetails,statistics&key={api_key}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "ContentCreation-Harvester/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for item in data.get("items", []):
            vid = item.get("id")
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            details = item.get("contentDetails", {})

            duration_sec = _parse_iso_duration(details.get("duration", "PT0S"))
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))
            eng_rate = round(((likes + comments) / views) * 100, 2) if views > 0 else 0.0

            results.append({
                "video_id": vid,
                "url": f"https://www.youtube.com/shorts/{vid}",
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "views": views,
                "likes": likes,
                "comments": comments,
                "engagement_rate": eng_rate,
                "duration_sec": duration_sec,
                "published_at": snippet.get("publishedAt", ""),
            })

    return results


def _fetch_single_metadata_ytdlp(video_id: str) -> dict[str, Any]:
    url = f"https://www.youtube.com/shorts/{video_id}"
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "logger": SilentYtdlLogger(),
        "skip_download": True,
        "extract_flat": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        },
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        views = int(info.get("view_count") or 0)
        likes = int(info.get("like_count") or 0)
        comments = int(info.get("comment_count") or 0)
        duration = float(info.get("duration") or 0.0)
        eng_rate = round(((likes + comments) / views) * 100, 2) if views > 0 else 0.0

        pub_raw = info.get("timestamp") or info.get("upload_date") or ""
        dt = parse_published_datetime(pub_raw)
        published_at = dt.isoformat() if dt else ""

        return {
            "video_id": video_id,
            "url": url,
            "title": info.get("title", ""),
            "channel": info.get("channel") or info.get("uploader", ""),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": eng_rate,
            "duration_sec": duration,
            "published_at": published_at,
        }


def harvest_channel_shorts(
    channel_handle: str,
    limit: int = 3,
    output_dir: str = "corpus/data",
    model_name: str = "gemini-3.8-flash",
    api_key: str | None = None,
) -> list[str]:
    urls = fetch_channel_shorts_urls(channel_handle, limit=limit)
    if not urls:
        logger.warning("No shorts found for %s", channel_handle)
        return []

    agent = ShortsIntelligenceAgent(
        gemini_model=model_name,
        output_dir=output_dir,
        youtube_api_key=api_key,
    )
    analyzed_ids: list[str] = []

    for idx, url in enumerate(urls, start=1):
        try:
            logger.info("Harvesting (%d/%d): %s", idx, len(urls), url)
            analysis = agent.analyze(url)
            analyzed_ids.append(analysis.video_id)
        except Exception as e:
            logger.error("Failed to harvest %s: %s", url, e)

    return analyzed_ids


def _scan_creator_candidates(
    creator: dict[str, Any],
    clean_cat: str,
    shorts_per_channel: int,
    scan_per_creator: int,
    min_views: int,
    min_duration: float,
    max_duration: float,
    existing_ids: set[str],
    days: int | None = None,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    handle = creator.get("handle")
    if not handle:
        return []

    try:
        effective_limit = max(scan_per_creator, int((days or 0) * 1.5), 35) if days else scan_per_creator
        shorts = fetch_channel_shorts_metadata(handle, limit=effective_limit, api_key=api_key)
        if not shorts:
            return []

        all_views = [s["views"] for s in shorts if s["views"] > 0]
        if not all_views:
            return []

        median_views = int(statistics.median(all_views))

        pool = []
        for s in shorts:
            dur = s.get("duration_sec", 0.0)
            if not ((min_duration - 2.0) <= dur <= (max_duration + 2.0)):
                continue
            if days and not is_within_days(s.get("published_at"), days):
                continue
            pool.append(s)

        if not pool:
            return []

        candidates: list[dict[str, Any]] = []

        for s in pool:
            v_id = s["video_id"]
            if v_id in existing_ids:
                continue
            if s["views"] < min_views:
                continue

            multiplier = round(s["views"] / max(median_views, 10_000), 2)
            eng = s["engagement_rate"]
            log_v = math.log10(max(s["views"], 1))
            score = round((multiplier * 0.60) + (min(eng, 20.0) * 0.25) + (log_v * 0.15), 2)

            candidates.append({
                "video_id": v_id,
                "url": s["url"],
                "title": s["title"],
                "channel": s["channel"],
                "category": clean_cat,
                "style_tags": creator.get("style_tags", []),
                "views": s["views"],
                "likes": s["likes"],
                "comments": s["comments"],
                "engagement_rate": eng,
                "duration_sec": s["duration_sec"],
                "published_at": s.get("published_at", ""),
                "channel_median_views": median_views,
                "outlier_multiplier": multiplier,
                "outlier_score": score,
            })

        candidates.sort(key=lambda c: (c["outlier_score"], c["views"]), reverse=True)
        return candidates[:shorts_per_channel]

    except Exception as e:
        logger.warning("Failed scanning creator %s: %s", handle, e)
        return []


def harvest_category_creators(
    category: str,
    shorts_per_channel: int = 4,
    category_target: int = 200,
    scan_per_creator: int = 25,
    min_views: int = 500_000,
    min_duration: float = 30.0,
    max_duration: float = 60.0,
    days: int | None = None,
    workers: int = 4,
    output_dir: str = "corpus/data",
    model_name: str = "gemini-3.8-flash",
    auto_synthesize: bool = True,
    api_key: str | None = None,
) -> list[str]:
    registry = load_creators_registry()
    clean_cat = category.strip().lower()

    if clean_cat not in registry:
        available = ", ".join(registry.keys())
        raise ValueError(f"Category '{category}' not found in registry. Available: {available}")

    creators = registry[clean_cat]
    existing_ids = get_existing_analyzed_ids(output_dir)

    timeline_str = f" | Timeline: past {days} days" if days else ""
    logger.info(
        "Harvesting category '%s': %d creators registered | Target: %d videos | Max %d/channel%s | Deduplicating against %d existing files...",
        clean_cat,
        len(creators),
        category_target,
        shorts_per_channel,
        timeline_str,
        len(existing_ids),
    )

    logger.info("Scanning %d channels in parallel for top outliers...", len(creators))
    all_candidates: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=min(len(creators), 8)) as scan_exec:
        futures = {
            scan_exec.submit(
                _scan_creator_candidates,
                creator=c,
                clean_cat=clean_cat,
                shorts_per_channel=shorts_per_channel,
                scan_per_creator=scan_per_creator,
                min_views=min_views,
                min_duration=min_duration,
                max_duration=max_duration,
                existing_ids=existing_ids,
                days=days,
                api_key=api_key,
            ): c
            for c in creators
        }
        for fut in as_completed(futures):
            creator_candidates = fut.result()
            all_candidates.extend(creator_candidates)

    all_candidates.sort(key=lambda c: (c["outlier_score"], c["views"]), reverse=True)
    selected_candidates = all_candidates[:category_target]

    logger.info(
        "Candidate pool ready: %d outlier shorts selected across %d creators. Starting parallel ingestion with %d workers...",
        len(selected_candidates),
        len({c['channel'] for c in selected_candidates}),
        workers,
    )

    if not selected_candidates:
        logger.info("No new unanalyzed outliers found matching the criteria in category '%s'.", clean_cat)
        return []

    agent = ShortsIntelligenceAgent(
        gemini_model=model_name,
        output_dir=output_dir,
        youtube_api_key=api_key,
    )

    lock = threading.Lock()
    completed_ids: list[str] = []
    counter = 0

    def _process_single_candidate(cand: dict[str, Any]) -> str | None:
        nonlocal counter
        v_id = cand["video_id"]

        with lock:
            if is_already_analyzed(v_id, output_dir):
                return v_id

        try:
            analysis = agent.analyze(cand["url"], save=True)
            if cand.get("category"):
                analysis.category = cand["category"]
            if cand.get("style_tags"):
                for st in cand["style_tags"]:
                    if st not in analysis.style_tags:
                        analysis.style_tags.append(st)

            out_file = Path(output_dir) / f"{analysis.video_id}.json"
            out_file.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")

            with lock:
                counter += 1
                completed_ids.append(analysis.video_id)
                logger.info(
                    "[%d/%d] Ingested %s ('%s' by %s | %s views, %.1fx median, score: %.2f)",
                    counter,
                    len(selected_candidates),
                    analysis.video_id,
                    analysis.title[:35],
                    cand["channel"],
                    f"{cand['views']:,}",
                    cand["outlier_multiplier"],
                    cand["outlier_score"],
                )
            return analysis.video_id

        except Exception as ex:
            logger.error("Failed analyzing candidate %s (%s): %s", v_id, cand["url"], ex)
            return None

    with ThreadPoolExecutor(max_workers=workers) as ingest_exec:
        ingest_futures = [
            ingest_exec.submit(_process_single_candidate, cand)
            for cand in selected_candidates
        ]
        for fut in as_completed(ingest_futures):
            fut.result()

    logger.info(
        "Category harvest complete: successfully ingested %d videos for '%s'.",
        len(completed_ids),
        clean_cat,
    )

    if auto_synthesize and completed_ids:
        try:
            from agents.pattern_agent import PatternSynthesisAgent
            logger.info("Updating pattern catalog with %d new analyses...", len(completed_ids))
            pattern_agent = PatternSynthesisAgent(gemini_model=model_name, data_dir=output_dir)
            pattern_agent.synthesize()
            logger.info("Pattern catalog successfully updated.")
        except Exception as e:
            logger.warning("Auto pattern synthesis failed: %s", e)

    return completed_ids
