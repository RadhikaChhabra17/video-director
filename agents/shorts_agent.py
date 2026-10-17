from __future__ import annotations

import json
import logging
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from corpus.schema import (
    CreatorSetup,
    EngagementMetrics,
    Platform,
    ShortsAnalysis,
    ToneTag,
)
from tools.downloader_tool import download_short_video, extract_media_info
from tools.graph_builder_tool import build_video_graph
from tools.multimodal_tool import analyze_shots_multimodal
from tools.youtube_tool import (
    extract_youtube_id,
    fetch_youtube_captions,
    fetch_youtube_metadata,
)

load_dotenv()

logger = logging.getLogger("ShortsIntelligenceAgent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


class ShortsIntelligenceAgent:
    def __init__(
        self,
        gemini_model: str = "gemini-3.8-flash",
        output_dir: str = "corpus/data",
        cache_dir: str = ".cache/videos",
        gemini_api_key: str | None = None,
        youtube_api_key: str | None = None,
    ) -> None:
        self.gemini_model = os.getenv("DIRECTOR_MODEL", gemini_model)
        self.output_dir = Path(output_dir)
        self.cache_dir = Path(cache_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.gemini_api_key = (
            gemini_api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("YOUTUBE_API_KEY")
        )
        self.youtube_api_key = youtube_api_key or os.getenv("YOUTUBE_API_KEY")

    def analyze(
        self,
        url_or_id: str,
        save: bool = True,
        cleanup_gemini_file: bool = True,
        force_reanalyze: bool = False,
    ) -> ShortsAnalysis:
        video_id, target_url, platform_type = extract_media_info(url_or_id)
        out_file = self.output_dir / f"{video_id}.json"

        if out_file.exists() and not force_reanalyze:
            logger.info("Media %s already analyzed. Loading cached analysis from %s", video_id, out_file)
            return ShortsAnalysis.model_validate_json(out_file.read_text(encoding="utf-8"))

        logger.info("Starting Autonomous Analysis for %s: %s", platform_type, video_id)

        video_path = download_short_video(
            url_or_id,
            cache_dir=str(self.cache_dir),
            max_height=720,
        )
        logger.info("Video stream ready at: %s", video_path)

        if platform_type == "youtube_shorts":
            meta = fetch_youtube_metadata(video_id, api_key=self.youtube_api_key)
            captions = fetch_youtube_captions(video_id)
            transcript_text = " ".join(c.get("text", "") for c in captions)
            resolved_platform = Platform.YOUTUBE_SHORTS
        else:
            title = Path(video_path).stem.replace("_", " ").title()
            duration = 15.0
            try:
                import subprocess
                cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    duration = float(res.stdout.strip())
            except Exception:
                pass

            channel_name = "Instagram Reel" if platform_type == "instagram_reels" else "Local Upload"
            meta = {
                "video_id": video_id,
                "url": target_url,
                "title": title,
                "channel": channel_name,
                "category": "lifestyle",
                "duration_sec": duration,
                "posted_at": datetime.now(timezone.utc),
                "views": 50000 if platform_type == "instagram_reels" else 1,
                "likes": 2500 if platform_type == "instagram_reels" else 1,
                "comments": 50 if platform_type == "instagram_reels" else 0,
                "engagement_rate": 5.0 if platform_type == "instagram_reels" else 100.0,
                "aspect_ratio": "9:16",
                "fps": 30.0,
            }
            transcript_text = ""
            resolved_platform = Platform.INSTAGRAM_REELS if platform_type == "instagram_reels" else (
                Platform.TIKTOK if platform_type == "tiktok" else Platform.YOUTUBE_SHORTS
            )

        logger.info(
            "Found video: '%s' | %s views | %s likes",
            meta["title"],
            f"{meta['views']:,}",
            f"{meta['likes']:,}",
        )

        logger.info(
            "Running multimodal shot perception with %s...",
            self.gemini_model,
        )
        shot_nodes = analyze_shots_multimodal(
            video_path=video_path,
            title=meta["title"],
            duration_sec=meta["duration_sec"],
            transcript_text=transcript_text,
            api_key=self.gemini_api_key,
            model_name=self.gemini_model,
            cleanup_remote_file=cleanup_gemini_file,
        )
        logger.info("Deconstructed video into %d dynamic shot nodes.", len(shot_nodes))

        video_graph, derived_features = build_video_graph(
            shots=shot_nodes,
            total_duration_sec=meta["duration_sec"],
        )
        logger.info(
            "Generated graph: %d nodes, %d directed edges | Pacing: %.1f cuts/10s",
            len(video_graph.nodes),
            len(video_graph.edges),
            derived_features.cuts_per_10s,
        )

        creator_setup = self._infer_creator_setup(shot_nodes)
        tone_tags = self._infer_tone_tags(shot_nodes, meta)
        style_tags = self._infer_style_tags(shot_nodes, meta, derived_features)
        virality_score = self._compute_virality_score(meta, derived_features)

        engagement = EngagementMetrics(
            views=meta["views"],
            likes=meta["likes"],
            comments=meta["comments"],
            shares=None,
            saves=None,
            engagement_rate=meta["engagement_rate"],
        )

        analysis = ShortsAnalysis(
            video_id=video_id,
            url=meta["url"],
            title=meta["title"],
            channel=meta["channel"],
            platform=resolved_platform,
            category=meta["category"],
            duration_sec=meta["duration_sec"],
            posted_at=meta["posted_at"],
            tone_tags=tone_tags,
            style_tags=style_tags,
            creator_setup=creator_setup,
            aspect_ratio=meta["aspect_ratio"],
            fps=meta.get("fps"),
            engagement=engagement,
            video_graph=video_graph,
            derived_features=derived_features,
            virality_score=virality_score,
        )

        if save:
            out_file = self.output_dir / f"{video_id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(analysis.model_dump_json(indent=2))
            logger.info("Saved analysis report to: %s", out_file)

        logger.info("Analysis completed successfully for '%s'!", meta["title"])
        return analysis

    def _infer_creator_setup(self, shots: list[Any]) -> CreatorSetup:
        speakers = set()
        for s in shots:
            if s.speaker_telemetry and s.speaker_telemetry.speaker_id:
                speakers.add(s.speaker_telemetry.speaker_id)

        if len(speakers) == 2:
            return CreatorSetup.DUO
        if len(speakers) > 2:
            return CreatorSetup.CREW
        return CreatorSetup.SOLO

    def _infer_tone_tags(self, shots: list[Any], meta: dict[str, Any]) -> list[ToneTag]:
        tones = set()
        durations = [
            s.timestamp_range.end_sec - s.timestamp_range.start_sec
            for s in shots
        ]
        avg_dur = sum(durations) / len(durations) if durations else 2.0
        if avg_dur < 1.4:
            tones.add(ToneTag.FAST)
            tones.add(ToneTag.ENERGETIC)
        elif avg_dur > 3.0:
            tones.add(ToneTag.SLOW)
            tones.add(ToneTag.CALM)

        for s in shots:
            if s.speaker_telemetry and s.speaker_telemetry.vocal_delivery:
                deliv = str(s.speaker_telemetry.vocal_delivery).lower()
                if "deadpan" in deliv:
                    tones.add(ToneTag.DEADPAN)
                if "excited" in deliv or "urgent" in deliv:
                    tones.add(ToneTag.ENERGETIC)
                if "playful" in deliv or "casual" in deliv:
                    tones.add(ToneTag.PLAYFUL)

        if not tones:
            tones.add(ToneTag.INFORMATIVE)

        return list(tones)[:4]

    def _infer_style_tags(
        self, shots: list[Any], meta: dict[str, Any], features: Any
    ) -> list[str]:
        tags = set()
        cuts = features.cuts_per_10s or 0.0
        if cuts >= 4.0:
            tags.add("FAST")
            tags.add("HIGH ENERGY")

        has_sfx = any(s.audio_style and s.audio_style.sfx_tags for s in shots)
        if has_sfx:
            tags.add("SFX-DRIVEN")

        movements = {s.camera.movement.value.lower() for s in shots if s.camera}
        if "whip" in movements or "tracking" in movements or "dolly" in movements:
            tags.add("CINEMATIC")
        if "handheld" in movements:
            tags.add("RAW")

        formats = {str(s.video_style.visual_format).lower() for s in shots if s.video_style}
        if "pov" in formats:
            tags.add("POV")
            tags.add("IMMERSIVE")
        if "talking_head" in formats and features.wpm and features.wpm > 170:
            tags.add("DIALOGUE-FIRST")

        title_lower = meta.get("title", "").lower()
        if any(w in title_lower for w in ["secret", "myth", "why", "how", "truth"]):
            tags.add("EDUCATIONAL")
            tags.add("STORY-DRIVEN")
        if any(w in title_lower for w in ["satisfying", "asmr", "crispy", "crunch"]):
            tags.add("ASMR")
            tags.add("SATISFYING")

        if not tags:
            tags.add("CINEMATIC")
            tags.add("STORY-DRIVEN")

        return sorted(tags)

    def _compute_virality_score(
        self, meta: dict[str, Any], features: Any
    ) -> float:
        views = meta.get("views", 0)
        eng_rate = meta.get("engagement_rate", 0.0) or 0.0

        view_score = min(math.log10(max(views, 1)) / 7.0, 1.0) * 0.4
        eng_score = min(eng_rate / 10.0, 1.0) * 0.35
        cuts = features.cuts_per_10s or 0.0
        pacing_score = min(cuts / 6.0, 1.0) * 0.15
        loop_score = (features.loopability or 0.5) * 0.10

        total = round(view_score + eng_score + pacing_score + loop_score, 2)
        return min(max(total, 0.0), 1.0)
