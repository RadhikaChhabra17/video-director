from __future__ import annotations

import json
import logging
import math
import os
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agents.shorts_agent import ShortsIntelligenceAgent
from tools.harvester_tool import (
    fetch_channel_shorts_metadata,
    get_existing_analyzed_ids,
    is_already_analyzed,
    is_within_days,
    load_creators_registry,
    parse_published_datetime,
    parse_timeline_days,
)
from tools.youtube_tool import extract_youtube_id

logger = logging.getLogger("OutlierTool")


class ShortOutlierCandidate(BaseModel):
    video_id: str
    url: str
    title: str
    channel: str
    category: str = "general"
    style_tags: list[str] = Field(default_factory=list)
    views: int = Field(ge=0)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    engagement_rate: float = Field(ge=0.0)
    duration_sec: float = Field(ge=0.0)
    published_at: str = ""
    channel_median_views: int = Field(ge=0)
    outlier_multiplier: float = Field(ge=0.0)
    outlier_score: float = Field(ge=0.0)


def find_channel_outliers(
    channel_handle: str,
    limit: int = 30,
    top_k: int = 5,
    min_views: int = 500_000,
    min_duration: float = 30.0,
    max_duration: float = 60.0,
    days: int | None = None,
    category: str = "general",
    style_tags: list[str] | None = None,
    api_key: str | None = None,
) -> list[ShortOutlierCandidate]:
    effective_limit = max(limit, int((days or 0) * 1.5), 35) if days else limit
    shorts = fetch_channel_shorts_metadata(channel_handle, limit=effective_limit, api_key=api_key)
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

    candidates: list[ShortOutlierCandidate] = []

    for s in pool:
        if s["views"] < min_views:
            continue

        multiplier = round(s["views"] / max(median_views, 10_000), 2)
        eng = s["engagement_rate"]
        log_views = math.log10(max(s["views"], 1))
        score = round((multiplier * 0.60) + (min(eng, 20.0) * 0.25) + (log_views * 0.15), 2)

        candidates.append(
            ShortOutlierCandidate(
                video_id=s["video_id"],
                url=s["url"],
                title=s["title"],
                channel=s["channel"],
                category=category,
                style_tags=list(style_tags or []),
                views=s["views"],
                likes=s["likes"],
                comments=s["comments"],
                engagement_rate=eng,
                duration_sec=s["duration_sec"],
                published_at=s.get("published_at", ""),
                channel_median_views=median_views,
                outlier_multiplier=multiplier,
                outlier_score=score,
            )
        )

    candidates.sort(key=lambda c: (c.outlier_score, c.views), reverse=True)
    return candidates[:top_k]


def find_category_outliers(
    category: str,
    creators_limit: int = 10,
    scan_per_creator: int = 25,
    shorts_per_channel: int = 4,
    min_views: int = 500_000,
    min_duration: float = 30.0,
    max_duration: float = 60.0,
    days: int | None = None,
    top_k: int = 10,
    registry_path: str | Path | None = None,
    api_key: str | None = None,
) -> list[ShortOutlierCandidate]:
    registry = load_creators_registry(registry_path)
    clean_cat = category.strip().lower()

    if clean_cat not in registry:
        available = ", ".join(registry.keys())
        raise ValueError(f"Category '{category}' not found in registry. Available: {available}")

    creators = registry[clean_cat][:creators_limit]
    timeline_str = f" (past {days} days)" if days else ""
    logger.info(
        "Scanning 30-60s outliers in '%s'%s across %d creators (%d videos each)...",
        clean_cat,
        timeline_str,
        len(creators),
        scan_per_creator,
    )

    all_candidates: list[ShortOutlierCandidate] = []

    for c in creators:
        handle = c.get("handle")
        if not handle:
            continue
        try:
            creator_tags = c.get("style_tags", [])
            outliers = find_channel_outliers(
                channel_handle=handle,
                limit=scan_per_creator,
                top_k=shorts_per_channel,
                min_views=min_views,
                min_duration=min_duration,
                max_duration=max_duration,
                days=days,
                category=clean_cat,
                style_tags=creator_tags,
                api_key=api_key,
            )
            all_candidates.extend(outliers)
        except Exception as e:
            logger.warning("Failed scanning creator %s: %s", handle, e)

    all_candidates.sort(key=lambda c: (c.outlier_score, c.views), reverse=True)
    return all_candidates[:top_k]


def find_cross_category_outliers_by_styles(
    style_tags: list[str],
    creators_per_category: int = 5,
    scan_per_creator: int = 20,
    min_views: int = 500_000,
    min_duration: float = 30.0,
    max_duration: float = 60.0,
    days: int | None = None,
    top_k: int = 10,
    registry_path: str | Path | None = None,
    api_key: str | None = None,
) -> list[ShortOutlierCandidate]:
    registry = load_creators_registry(registry_path)
    normalized_target_styles = {t.strip().upper() for t in style_tags}

    timeline_str = f" (past {days} days)" if days else ""
    logger.info(
        "Mining cross-category outliers matching style tags: %s%s...",
        list(normalized_target_styles),
        timeline_str,
    )

    all_candidates: list[ShortOutlierCandidate] = []

    for cat_name, creators_list in registry.items():
        matched_creators = []
        for c in creators_list:
            c_tags = {t.strip().upper() for t in c.get("style_tags", [])}
            if normalized_target_styles.intersection(c_tags):
                matched_creators.append(c)

        selected_creators = matched_creators[:creators_per_category] if matched_creators else creators_list[:2]

        for c in selected_creators:
            handle = c.get("handle")
            if not handle:
                continue
            try:
                creator_tags = c.get("style_tags", [])
                outliers = find_channel_outliers(
                    channel_handle=handle,
                    limit=scan_per_creator,
                    top_k=2,
                    min_views=min_views,
                    min_duration=min_duration,
                    max_duration=max_duration,
                    days=days,
                    category=cat_name,
                    style_tags=creator_tags,
                    api_key=api_key,
                )
                all_candidates.extend(outliers)
            except Exception as e:
                logger.warning("Failed scanning creator %s: %s", handle, e)

    all_candidates.sort(key=lambda c: (c.outlier_score, c.views), reverse=True)
    return all_candidates[:top_k]


def harvest_outlier_candidates(
    candidates: list[ShortOutlierCandidate],
    agent: ShortsIntelligenceAgent | None = None,
    output_dir: str = "corpus/data",
    workers: int = 4,
    auto_synthesize: bool = True,
) -> list[Any]:
    if not candidates:
        logger.warning("No outlier candidates provided to harvest.")
        return []

    existing_ids = get_existing_analyzed_ids(output_dir)
    pending_candidates = [c for c in candidates if c.video_id not in existing_ids]

    logger.info(
        "Harvest queue: %d total candidates | %d already in %s (skipped) | %d pending analysis",
        len(candidates),
        len(candidates) - len(pending_candidates),
        output_dir,
        len(pending_candidates),
    )

    if not pending_candidates:
        logger.info("All candidate videos already analyzed in %s. Nothing new to ingest.", output_dir)
        return []

    resolved_agent = agent or ShortsIntelligenceAgent(output_dir=output_dir)
    lock = threading.Lock()
    results: list[Any] = []
    counter = 0

    def _process_candidate(c: ShortOutlierCandidate) -> Any:
        nonlocal counter
        try:
            analysis = resolved_agent.analyze(c.url, save=True)
            if c.category:
                analysis.category = c.category
            if c.style_tags:
                for st in c.style_tags:
                    if st not in analysis.style_tags:
                        analysis.style_tags.append(st)

            out_file = Path(output_dir) / f"{analysis.video_id}.json"
            out_file.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")

            with lock:
                counter += 1
                results.append(analysis)
                logger.info(
                    "[%d/%d] Ingested outlier %s ('%s' by %s | %s views, %.1fx median, score: %.2f)",
                    counter,
                    len(pending_candidates),
                    c.video_id,
                    c.title[:35],
                    c.channel,
                    f"{c.views:,}",
                    c.outlier_multiplier,
                    c.outlier_score,
                )
            return analysis
        except Exception as e:
            logger.error("Failed to analyze outlier %s (%s): %s", c.video_id, c.url, e)
            return None

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_process_candidate, c) for c in pending_candidates]
        for fut in as_completed(futures):
            fut.result()

    if auto_synthesize and results:
        try:
            from agents.pattern_agent import PatternSynthesisAgent
            pattern_agent = PatternSynthesisAgent(data_dir=output_dir)
            pattern_agent.synthesize()
            logger.info("Pattern catalog successfully updated with outlier analyses.")
        except Exception as e:
            logger.warning("Failed to auto-synthesize patterns: %s", e)

    return results
