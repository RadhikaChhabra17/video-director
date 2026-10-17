from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from corpus.pattern_schema import PatternCatalog, ViralPatternEntry, create_empty_catalog
from tools.pattern_tools import (
    evaluate_pattern_match,
    get_genai_client,
    has_sufficient_structural_evidence,
    load_corpus_analyses,
    load_pattern_catalog,
    merge_video_into_pattern,
    save_director_context,
    save_pattern_catalog,
    synthesize_novel_pattern,
)

logger = logging.getLogger("PatternSynthesisAgent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


class PatternSynthesisAgent:
    def __init__(
        self,
        gemini_model: str = "gemini-3.8-flash",
        catalog_path: str = "corpus/pattern_catalog.json",
        director_context_path: str = "corpus/director_context.json",
        data_dir: str = "corpus/data",
        api_key: str | None = None,
    ) -> None:
        self.gemini_model = os.getenv("DIRECTOR_MODEL", gemini_model)
        self.catalog_path = Path(catalog_path)
        self.director_context_path = Path(director_context_path)
        self.data_dir = Path(data_dir)
        self.api_key = api_key
        self.client = get_genai_client(api_key=api_key)

    def get_catalog(self) -> PatternCatalog:
        return load_pattern_catalog(self.catalog_path)

    def synthesize(
        self,
        force_rebuild: bool = False,
        video_ids: set[str] | list[str] | None = None,
        max_videos: int | None = None,
    ) -> PatternCatalog:
        analyses = load_corpus_analyses(self.data_dir)
        if not analyses:
            logger.warning("No video analysis files found in %s", self.data_dir)
            return self.get_catalog()

        if force_rebuild:
            logger.info("Force rebuild requested. Initializing empty catalog...")
            catalog = create_empty_catalog()
        else:
            catalog = load_pattern_catalog(self.catalog_path)

        already_cataloged: set[str] = set()
        for p in catalog.patterns:
            already_cataloged.update(p.source_video_ids)

        pending = [v for v in analyses if v.video_id not in already_cataloged]
        
        # Filter to specific video IDs if requested
        if video_ids is not None:
            target_ids = set(video_ids)
            pending = [v for v in pending if v.video_id in target_ids]

        # Stably sort pending videos by view count descending so top outliers seed foundation archetypes
        pending.sort(key=lambda v: (v.engagement.views, v.video_id), reverse=True)

        if max_videos is not None and max_videos > 0:
            pending = pending[:max_videos]

        logger.info(
            "Corpus has %d analyses. Already cataloged: %d. Pending processing: %d.",
            len(analyses),
            len(already_cataloged),
            len(pending),
        )

        if not pending:
            logger.info("Pattern catalog is already up to date.")
            save_director_context(catalog, self.director_context_path)
            return catalog

        def _persist_catalog_snapshot():
            catalog.total_corpus_videos = sum(p.frequency for p in catalog.patterns)
            catalog.total_views_analyzed = sum(p.aggregate_views for p in catalog.patterns)
            save_pattern_catalog(catalog, self.catalog_path)
            save_director_context(catalog, self.director_context_path)

        try:
            for idx, video in enumerate(pending, start=1):
                try:
                    logger.info(
                        "[%d/%d] Processing video %s ('%s', %s views)...",
                        idx,
                        len(pending),
                        video.video_id,
                        video.title[:35],
                        f"{video.engagement.views:,}",
                    )

                    decision = evaluate_pattern_match(
                        video=video,
                        catalog=catalog,
                        client=self.client,
                        model_name=self.gemini_model,
                    )

                    # Rule 1: High confidence (>= 0.70) match (same or variant) -> Merge into existing pattern
                    if decision.is_match and decision.matched_pattern_id and decision.match_confidence >= 0.70:
                        matched_pattern = next(
                            (p for p in catalog.patterns if p.pattern_id == decision.matched_pattern_id),
                            None,
                        )
                        if matched_pattern:
                            merge_video_into_pattern(
                                pattern=matched_pattern,
                                video=video,
                                suggested_guidelines=decision.suggested_guidelines_to_add,
                            )
                            logger.info(
                                "--> MATCHED (%s, conf=%.2f): Merged %s into '%s' (%s). New frequency: %d. Aggregate views: %s.",
                                decision.relationship,
                                decision.match_confidence,
                                video.video_id,
                                matched_pattern.name,
                                matched_pattern.pattern_id,
                                matched_pattern.frequency,
                                f"{matched_pattern.aggregate_views:,}",
                            )
                            if idx % 3 == 0:
                                _persist_catalog_snapshot()
                            time.sleep(4.0)
                            continue

                    # Rule 2: Genuinely novel archetype with high confidence (>= 0.70) AND verified structural evidence
                    has_evidence, evidence_reason = has_sufficient_structural_evidence(video)
                    if not decision.is_match and decision.match_confidence >= 0.70 and has_evidence:
                        logger.info(
                            "--> NOVEL (conf=%.2f, %s): Synthesizing new pattern archetype for %s...",
                            decision.match_confidence,
                            evidence_reason,
                            video.video_id,
                        )
                        # Brief spacing between match evaluation and novel synthesis API calls
                        time.sleep(2.0)
                        existing_ids = {p.pattern_id for p in catalog.patterns}
                        new_pattern = synthesize_novel_pattern(
                            video=video,
                            client=self.client,
                            model_name=self.gemini_model,
                            existing_pattern_ids=existing_ids,
                        )

                        if new_pattern.pattern_id in existing_ids:
                            new_pattern.pattern_id = f"{new_pattern.pattern_id}_{video.video_id}"

                        catalog.patterns.append(new_pattern)
                        logger.info(
                            "--> CREATED: '%s' (%s) with %d macro beats and %s views.",
                            new_pattern.name,
                            new_pattern.pattern_id,
                            len(new_pattern.narrative_beat_sequence),
                            f"{new_pattern.aggregate_views:,}",
                        )
                        if idx % 3 == 0:
                            _persist_catalog_snapshot()
                        time.sleep(4.0)
                        continue

                    # Rule 3: Moderate confidence (0.50 <= conf < 0.70)
                    # Soft merge ONLY IF model identified relationship as same/variant AND creator setup matches
                    if (
                        decision.matched_pattern_id
                        and decision.relationship in ("same", "variant")
                        and decision.match_confidence >= 0.50
                    ):
                        matched_pattern = next(
                            (p for p in catalog.patterns if p.pattern_id == decision.matched_pattern_id),
                            None,
                        )
                        if matched_pattern and video.creator_setup == matched_pattern.creator_setup:
                            logger.info(
                                "--> VARIANT MERGE (conf=%.2f): Merging %s into '%s' as stylistic variant.",
                                decision.match_confidence,
                                video.video_id,
                                matched_pattern.name,
                            )
                            merge_video_into_pattern(
                                pattern=matched_pattern,
                                video=video,
                                suggested_guidelines=decision.suggested_guidelines_to_add,
                            )
                            if idx % 3 == 0:
                                _persist_catalog_snapshot()
                            time.sleep(4.0)
                            continue

                    # Rule 4: Low confidence, structural divergence, or incomplete evidence -> Flag / skip
                    logger.warning(
                        "--> SKIPPED / FLAGGED: %s ('%s') had low confidence (%.2f), divergent structure (%s), or insufficient evidence (%s). Not creating premature archetype.",
                        video.video_id,
                        video.title[:30],
                        decision.match_confidence,
                        decision.relationship,
                        evidence_reason if not has_evidence else "ambiguous taxonomy",
                    )

                    if idx % 3 == 0:
                        _persist_catalog_snapshot()

                    # Polite pacing sleep to stay well within free-tier API rate limits
                    time.sleep(4.0)

                except Exception as e:
                    logger.error(
                        "--> ERROR processing %s ('%s'): %s. Persisting catalog and continuing.",
                        video.video_id,
                        video.title[:30],
                        e,
                    )
                    _persist_catalog_snapshot()
                    time.sleep(10.0)
                    continue

        except KeyboardInterrupt:
            logger.warning("Synthesis interrupted by user. Saving current progress...")
            _persist_catalog_snapshot()
        finally:
            _persist_catalog_snapshot()

        logger.info(
            "Pattern catalog updated at %s: %d distinct archetypes, %d total videos, %s views analyzed.",
            self.catalog_path,
            len(catalog.patterns),
            catalog.total_corpus_videos,
            f"{catalog.total_views_analyzed:,}",
        )
        logger.info("Director-ready context exported to %s.", self.director_context_path)
        return catalog
