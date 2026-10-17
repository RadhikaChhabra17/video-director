from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from agents.director_agent import DirectorAgent
from agents.pattern_agent import PatternSynthesisAgent
from agents.shorts_agent import ShortsIntelligenceAgent
from agents.video_agent import VideoGenerationAgent
from corpus.director_schema import DirectorResponseManifest
from corpus.pattern_schema import PatternCatalog
from tools.harvester_tool import (
    get_existing_analyzed_ids,
    harvest_category_creators,
    harvest_channel_shorts,
    load_creators_registry,
    parse_published_datetime,
    parse_timeline_days,
)
from tools.outlier_tool import (
    ShortOutlierCandidate,
    find_category_outliers,
    find_channel_outliers,
    find_cross_category_outliers_by_styles,
    harvest_outlier_candidates,
)
from tools.pattern_tools import load_pattern_catalog


def display_catalog(catalog: PatternCatalog) -> None:
    print("\n" + "=" * 70)
    print("                    VIRAL PATTERN CATALOG")
    print("=" * 70)
    print(f"Total Archetypes:      {len(catalog.patterns)}")
    print(f"Total Videos Merged:   {catalog.total_corpus_videos}")
    print(f"Total Views Analyzed:  {catalog.total_views_analyzed:,}")
    print(f"Last Updated:          {catalog.updated_at.isoformat()}")
    print("=" * 70)

    for idx, p in enumerate(catalog.patterns, start=1):
        print(f"\n[{idx}] {p.name.upper()} ({p.pattern_id})")
        print(f"    Archetype:    {p.archetype}")
        print(f"    Setup:        {p.creator_setup.value.upper()}")
        if p.style_tags:
            print(f"    Style Tags:   {', '.join(p.style_tags)}")
        if p.tone_tags:
            print(f"    Tones:        {', '.join([t.value for t in p.tone_tags])}")
        if p.best_use_cases:
            print(f"    Best For:     {'; '.join(p.best_use_cases)}")
        print(f"    Videos:       {p.frequency} (IDs: {', '.join(p.source_video_ids)})")
        print(f"    Agg Views:    {p.aggregate_views:,} | Avg Eng: {p.avg_engagement_rate:.2f}%")
        print(f"    Hook Formula: {p.hook_recipe.formula}")
        print(f"    First 3s:     {p.hook_recipe.first_3s_action}")
        beats_str = " -> ".join([b.value.upper() for b in p.narrative_beat_sequence])
        print(f"    Beats:        {beats_str}")
        opt_range = p.pacing_benchmarks.optimal_duration_range_sec
        range_str = f"{opt_range[0]:.0f}s - {opt_range[1]:.0f}s" if len(opt_range) >= 2 else "n/a"
        print(
            f"    Pacing:       {p.pacing_benchmarks.target_cuts_per_10s} cuts/10s | "
            f"ASL: {p.pacing_benchmarks.target_asl_sec}s | "
            f"Range: {range_str}"
        )
        print("    Director Guidelines:")
        for g in p.director_guidelines:
            print(f"      * {g}")
    print("\n" + "=" * 70 + "\n")


def display_director_manifest(manifest: DirectorResponseManifest) -> None:
    print("\n" + "=" * 70)
    print("               DIRECTOR AGENT: SHOT-BY-SHOT BLUEPRINT")
    print("=" * 70)
    print(f"Project ID:      {manifest.project_id}")
    print(f"Title:           {manifest.title}")
    print(f"Concept:         {manifest.concept_summary}")
    print(f"Blueprint:       {manifest.pattern_blueprint_id}")
    print(f"Duration:        {manifest.total_target_duration_sec:.1f}s | {manifest.resolution} {manifest.aspect_ratio} @ {manifest.fps}fps")
    if manifest.visual_style_anchor:
        print(f"Style Anchor:    {manifest.visual_style_anchor}")
    print("-" * 70)

    cum_time = 0.0
    for shot in manifest.shots:
        start_time = cum_time
        cum_time += shot.duration_sec
        hook_tag = "[HOOK CRITICAL]" if shot.is_hook_critical else ""
        req_tag = f" [REQ: {', '.join(shot.satisfied_requirement_ids)}]" if getattr(shot, "satisfied_requirement_ids", None) else ""
        print(
            f"\n>> {shot.shot_id.upper()} ({start_time:.1f}s - {cum_time:.1f}s | {shot.duration_sec:.1f}s) "
            f"BEAT: {shot.beat_name.value.upper()} {hook_tag}{req_tag}"
        )

        vis = shot.visual
        cam_info = f"{vis.framing.value.upper()} | {vis.camera_movement.value.upper()}"
        print(f"   Visual Format: {vis.format.value} | Camera: {cam_info}")
        print(f"   Action:        {vis.subject_action}")
        if vis.face_expression:
            print(f"   Expression:    {vis.face_expression} (Gaze: {vis.gaze_direction})")
        print(f"   Scene:         \"{vis.scene_description[:80]}...\"")

        if shot.audio.speech:
            sp = shot.audio.speech
            print(f"   Dialogue:      \"{sp.transcript}\" [{sp.vocal_delivery}]")
        if shot.audio.sfx_cues:
            sfx_str = ", ".join([f"{s.sfx_name} @ +{s.trigger_offset_sec:.1f}s" for s in shot.audio.sfx_cues])
            print(f"   SFX Cues:      {sfx_str}")

        if shot.overlays and shot.overlays.captions:
            cap = shot.overlays.captions
            hl = f" (Highlight: {', '.join(cap.highlight_words)})" if cap.highlight_words else ""
            print(f"   Captions:      \"{cap.text}\"{hl}")

        trans = shot.transition_out
        snap_zoom = " + SNAP ZOOM" if trans.vfx_snap_zoom else ""
        print(f"   Transition:    {trans.transition_type.value.upper()}{snap_zoom}")

    if getattr(manifest, "deterministic_validation", None):
        det = getattr(manifest, "deterministic_validation")
        print("-" * 70)
        status_text = "ALL PHYSICAL CHECKS PASSED" if det.all_passed else "ATTENTION NEEDED"
        print(f"DETERMINISTIC VALIDATOR: {status_text} ({det.passed_count + det.auto_healed_count}/{det.total_checks} Checks Passed, {det.auto_healed_count} Auto-Healed)")
        for chk in det.checks:
            tag = chk.status.upper()
            print(f"  * [{chk.check_id}] {chk.name}: {tag}")
            for d in chk.details:
                print(f"      -> {d}")

    if getattr(manifest, "compliance_audit", None):
        audit = getattr(manifest, "compliance_audit")
        print("-" * 70)
        status_text = "ALL HARD CONSTRAINTS SATISFIED" if audit.all_hard_constraints_satisfied else "PARTIAL COMPLIANCE"
        print(f"REQUIREMENT AUDITOR: {status_text} ({audit.compliance_rate_pct:.0f}% Compliance)")
        print(f"  * Verified: {audit.passed_count}/{audit.total_requirements} atomic requirements verified without contradiction")
        if audit.auditor_summary:
            print(f"  * Summary:  {audit.auditor_summary}")

    if getattr(manifest, "creative_reasoning", None):
        cr = getattr(manifest, "creative_reasoning")
        print("-" * 70)
        print("CREATIVE REASONING ENGINE (WHAT IS INTERESTING HERE?):")
        print(f"  * Emotional Story: {cr.inferred_emotional_story}")
        print(f"  * Creator Voice:   {cr.creator_authentic_voice}")
        if cr.unusual_moments_discovered:
            print("  * Unusual Moments Discovered:")
            for m in cr.unusual_moments_discovered:
                print(f"    - {m}")
        print(f"  * Competing Alternatives Explored ({len(cr.alternatives)}):")
        for alt in cr.alternatives:
            print(f"    - [{alt.angle_id}] {alt.title}: {alt.angle_concept}")

    if getattr(manifest, "optimization_decision", None):
        opt = getattr(manifest, "optimization_decision")
        print("-" * 70)
        print("OPTIMIZATION ENGINE (WHICH EDIT IS STRONGEST?):")
        print(f"  * Selected Champion Angle: {opt.selected_angle_id}")
        print(f"  * Selection Rationale:     {opt.selection_rationale}")
        if opt.synthesis_enhancements:
            print("  * Synthesis Enhancements Borrowed:")
            for s in opt.synthesis_enhancements:
                print(f"    - {s}")
        if opt.revision_directives:
            print("  * Revisions Constructed into Manifest:")
            for r in opt.revision_directives:
                print(f"    - {r}")

    if manifest.director_notes:
        print("\n" + "-" * 70)
        print("Director Notes:")
        for note in manifest.director_notes:
            print(f"  * {note}")
    print("=" * 70 + "\n")


def display_creators_registry(registry_path: str = "corpus/creators_registry.json") -> None:
    registry = load_creators_registry(registry_path)
    if not registry:
        print("Registry file not found or empty.")
        return

    print("\n" + "=" * 75)
    print("                 TOP CREATORS REGISTRY (50 PER CATEGORY)")
    print("=" * 75)
    for cat, creators in registry.items():
        print(f"\n[{cat.upper()}] ({len(creators)} Creators)")
        print("-" * 75)
        for idx, c in enumerate(creators, start=1):
            tags_str = f"[{', '.join(c.get('style_tags', []))}]" if c.get("style_tags") else ""
            print(f"  {idx:2d}. {c['name']:<28} {c['handle']:<22} {tags_str}")
    print("\n" + "=" * 75 + "\n")


def display_outliers(candidates: list[ShortOutlierCandidate]) -> None:
    print("\n" + "=" * 75)
    print("                 STATISTICAL OUTLIER SHORTS DISCOVERED")
    print("=" * 75)
    if not candidates:
        print("No outlier candidates met the criteria.")
        print("=" * 75 + "\n")
        return

    now = datetime.now(timezone.utc)
    for idx, c in enumerate(candidates, start=1):
        print(f"\n[{idx}] {c.title}")
        print(f"    Channel:    {c.channel} ({c.category.upper()})")
        if c.style_tags:
            print(f"    Styles:     {', '.join(c.style_tags)}")
        if c.published_at:
            dt = parse_published_datetime(c.published_at)
            if dt:
                days_ago = max(0, int((now - dt).total_seconds() / 86400.0))
                date_str = dt.strftime("%Y-%m-%d")
                print(f"    Published:  {date_str} ({days_ago}d ago)")
        print(f"    Views:      {c.views:,} ({c.outlier_multiplier:.1f}x channel median of {c.channel_median_views:,})")
        print(f"    Engagement: {c.engagement_rate:.2f}% | Duration: {c.duration_sec:.1f}s | Score: {c.outlier_score:.1f}")
        print(f"    URL:        {c.url}")
    print("\n" + "=" * 75 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous Multimodal YouTube Shorts & Pattern Intelligence System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "url_or_id",
        nargs="?",
        default=None,
        help="YouTube Shorts URL or 11-character video ID for single video analysis",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("DIRECTOR_MODEL", "gemini-3.8-flash"),
        help="Gemini model for multimodal perception, pattern synthesis, and directing",
    )
    parser.add_argument(
        "--output-dir",
        default="corpus/data",
        help="Directory to save output JSON analysis reports",
    )
    parser.add_argument(
        "--catalog-path",
        default="corpus/pattern_catalog.json",
        help="Path to the viral pattern catalog JSON",
    )
    parser.add_argument(
        "--director-context-path",
        default="corpus/director_context.json",
        help="Path to the trimmed director context JSON",
    )
    parser.add_argument(
        "--director-output-dir",
        default="corpus/director_output",
        help="Directory to save director response manifests",
    )
    parser.add_argument(
        "--direct",
        type=str,
        default=None,
        help="Script or idea text (or path to script file) to direct into a full video blueprint",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Target category context for directing or filtering (tech, food, travel, science, entertainment)",
    )
    parser.add_argument(
        "--styles",
        type=str,
        default=None,
        help="Comma-separated style tags (e.g. 'FAST,CINEMATIC,HIGH ENERGY,SFX-DRIVEN')",
    )
    parser.add_argument(
        "--pattern-id",
        type=str,
        default=None,
        help="Specific viral pattern blueprint ID to enforce for directing",
    )
    parser.add_argument(
        "--target-duration",
        type=float,
        default=None,
        help="Target total video duration in seconds for directing (e.g. 10 to 60 seconds)",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=30.0,
        help="Minimum duration floor in seconds for Shorts filtering (e.g. 30)",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=60.0,
        help="Maximum duration ceiling in seconds for Shorts filtering (e.g. 60)",
    )
    parser.add_argument(
        "--harvest-channel",
        type=str,
        default=None,
        help="Channel handle (e.g. '@Mrwhosetheboss') or channel URL to harvest top shorts from",
    )
    parser.add_argument(
        "--harvest-category",
        type=str,
        default=None,
        help="Category name to harvest creators from (tech, food, travel, science, entertainment)",
    )
    parser.add_argument(
        "--find-outliers",
        type=str,
        default=None,
        help="Find statistical 30-60s outliers for a category (tech, food, travel, science, entertainment) or handle",
    )
    parser.add_argument(
        "--find-style-outliers",
        type=str,
        default=None,
        help="Find cross-category outliers matching specific style tags (e.g. 'CINEMATIC,IMMERSIVE')",
    )
    parser.add_argument(
        "--harvest-outliers",
        type=str,
        default=None,
        help="Discover, download, analyze, and synthesize outlier shorts for category or channel handle",
    )
    parser.add_argument(
        "--min-views",
        type=int,
        default=500_000,
        help="Minimum view count floor for outlier filtering",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of shorts to harvest per creator or top outliers to select",
    )
    parser.add_argument(
        "--creators-limit",
        type=int,
        default=5,
        help="Number of creators to scan when using category find commands",
    )
    parser.add_argument(
        "--shorts-per-channel",
        type=int,
        default=4,
        help="Max number of shorts to ingest per creator (typically 2 to 4)",
    )
    parser.add_argument(
        "--category-target",
        type=int,
        default=200,
        help="Total target number of videos to harvest for the category (e.g. 200 to 250)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Filter videos published within the last N days (e.g. 15 for past 15 days, 30 for past month)",
    )
    parser.add_argument(
        "--timeline",
        type=str,
        default=None,
        help="Timeline window string (e.g. '15d', '30d', '1m', '15', '30')",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent worker threads for parallel video analysis",
    )
    parser.add_argument(
        "--force-reanalyze",
        action="store_true",
        help="Force re-analyzing videos even if already present in corpus/data",
    )
    parser.add_argument(
        "--list-creators",
        action="store_true",
        help="List all top 50 creators per category from creators_registry.json",
    )
    parser.add_argument(
        "--synthesize-patterns",
        "--patterns",
        action="store_true",
        help="Synthesize and merge pattern catalog from all video analyses in corpus/data",
    )
    parser.add_argument(
        "--rebuild-patterns",
        action="store_true",
        help="Force rebuild pattern catalog from scratch, reprocessing all analyses",
    )
    parser.add_argument(
        "--pattern-limit",
        type=int,
        default=None,
        help="Maximum number of pending videos to process during pattern synthesis",
    )
    parser.add_argument(
        "--view-patterns",
        action="store_true",
        help="Display summary of current pattern catalog",
    )
    parser.add_argument(
        "--view-director-context",
        action="store_true",
        help="Display trimmed director context JSON",
    )
    parser.add_argument(
        "--render",
        type=str,
        default=None,
        help="Path to director manifest JSON to render using Gemini Omni 1.1 Flash",
    )
    parser.add_argument(
        "--render-resolution",
        type=str,
        default=None,
        choices=["360p", "720p", "1080p", "4k"],
        help="Target video render resolution (defaults to 720p or manifest setting)",
    )
    parser.add_argument(
        "--render-concurrency",
        type=int,
        default=2,
        help="Concurrent shots to generate simultaneously via Gemini Omni",
    )
    parser.add_argument(
        "--first-frame",
        type=str,
        default=None,
        help="Path to initial reference portrait/frame for character consistency",
    )
    parser.add_argument(
        "--render-video",
        action="store_true",
        help="Automatically trigger video generation immediately after directing",
    )
    parser.add_argument(
        "--ingest-dir",
        type=str,
        default=None,
        help="Directory containing video files (.mp4, .mov) to batch analyze and ingest into corpus/data",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip saving analysis JSON or director manifest to disk",
    )
    parser.add_argument(
        "--analyze-only",
        "--no-synthesize",
        action="store_true",
        help="Only perform raw video perception and save to corpus/data without running pattern synthesis",
    )
    parser.add_argument(
        "--video-limit",
        type=int,
        default=None,
        help="Limit number of videos to analyze from a .txt list or ingest directory",
    )
    parser.add_argument(
        "--extract-audio",
        action="store_true",
        help="Extract audio track (.mp3) from video URL(s), .txt list, or cache into audio_exports/",
    )
    parser.add_argument(
        "--retrain-techniques",
        action="store_true",
        help="Retrain and refresh corpus/technique_library.json against all analyzed corpus video graphs",
    )

    args = parser.parse_args()

    resolved_days = args.days or parse_timeline_days(args.timeline)
    parsed_style_tags = [s.strip().upper() for s in args.styles.split(",")] if args.styles else None

    if args.retrain_techniques:
        from tools.retrain_technique_library import retrain_technique_library
        retrain_technique_library()
        return

    if args.list_creators:
        display_creators_registry()
        return

    if args.view_director_context:
        catalog = load_pattern_catalog(args.catalog_path)
        print(json.dumps(catalog.to_director_context(), indent=2))
        return

    if args.view_patterns:
        catalog = load_pattern_catalog(args.catalog_path)
        display_catalog(catalog)
        return

    if args.find_style_outliers:
        styles_query = [s.strip().upper() for s in args.find_style_outliers.split(",")]
        timeline_info = f" | Timeline: past {resolved_days} days" if resolved_days else ""
        print(f"\nMining cross-category 30-60s outliers matching styles: {styles_query}{timeline_info}...")
        outliers = find_cross_category_outliers_by_styles(
            style_tags=styles_query,
            creators_per_category=args.creators_limit,
            scan_per_creator=20,
            min_views=args.min_views,
            min_duration=args.min_duration,
            max_duration=args.max_duration,
            days=resolved_days,
            top_k=args.limit,
        )
        display_outliers(outliers)
        return

    if args.ingest_dir:
        ingest_path = Path(args.ingest_dir)
        if not ingest_path.exists() or not ingest_path.is_dir():
            print(f"Error: Directory '{args.ingest_dir}' not found.")
            return

        video_extensions = {".mp4", ".mov", ".webm", ".mkv"}
        video_files = sorted([f for f in ingest_path.iterdir() if f.suffix.lower() in video_extensions])
        if not video_files:
            print(f"No video files (.mp4, .mov, .webm, .mkv) found in {ingest_path}")
            return

        print(f"\nDiscovered {len(video_files)} video file(s) in {ingest_path} to ingest into corpus...")
        agent = ShortsIntelligenceAgent(
            gemini_model=args.model,
            output_dir=args.output_dir,
        )

        if args.video_limit is not None and args.video_limit > 0:
            video_files = video_files[:args.video_limit]

        success_count = 0
        ingested_video_ids = []
        for idx, vf in enumerate(video_files, start=1):
            print(f"\n[{idx}/{len(video_files)}] Analyzing {vf.name}...")
            try:
                analysis = agent.analyze(str(vf), save=not args.no_save, force_reanalyze=args.force_reanalyze)
                print(f"  -> Successfully analyzed '{analysis.title}' ({len(analysis.video_graph.nodes)} shots, Virality: {analysis.virality_score:.2f})")
                ingested_video_ids.append(analysis.video_id)
                success_count += 1
            except Exception as e:
                print(f"  -> Failed to analyze {vf.name}: {e}")

        print(f"\nIngested {success_count}/{len(video_files)} videos successfully.")
        if args.analyze_only:
            print("Skipping pattern synthesis (--analyze-only requested).")
            return
        print("Synthesizing pattern catalog from updated corpus...")
        pattern_agent = PatternSynthesisAgent(
            gemini_model=args.model,
            catalog_path=args.catalog_path,
            director_context_path=args.director_context_path,
            data_dir=args.output_dir,
        )
        catalog = pattern_agent.synthesize(
            force_rebuild=args.rebuild_patterns,
            video_ids=ingested_video_ids if not args.rebuild_patterns else None,
            max_videos=args.pattern_limit,
        )
        display_catalog(catalog)
        return

    if args.find_outliers:
        target = args.find_outliers.strip()
        timeline_info = f" | Timeline: past {resolved_days} days" if resolved_days else ""
        print(f"\nMining statistical 30-60s outliers for '{target}' (min {args.min_views:,} views{timeline_info})...")
        if target.startswith("@") or target.startswith("http"):
            outliers = find_channel_outliers(
                channel_handle=target,
                limit=30,
                top_k=args.limit,
                min_views=args.min_views,
                min_duration=args.min_duration,
                max_duration=args.max_duration,
                days=resolved_days,
            )
        else:
            outliers = find_category_outliers(
                category=target,
                creators_limit=args.creators_limit,
                scan_per_creator=25,
                shorts_per_channel=args.shorts_per_channel,
                min_views=args.min_views,
                min_duration=args.min_duration,
                max_duration=args.max_duration,
                days=resolved_days,
                top_k=args.limit,
            )
        display_outliers(outliers)
        return

    if args.harvest_outliers:
        target = args.harvest_outliers.strip()
        timeline_info = f" (past {resolved_days} days)" if resolved_days else ""
        print(f"\nMining and harvesting top 30-60s outliers for '{target}'{timeline_info}...")
        if target.startswith("@") or target.startswith("http"):
            outliers = find_channel_outliers(
                channel_handle=target,
                limit=30,
                top_k=args.limit,
                min_views=args.min_views,
                min_duration=args.min_duration,
                max_duration=args.max_duration,
                days=resolved_days,
            )
        else:
            outliers = find_category_outliers(
                category=target,
                creators_limit=args.creators_limit,
                scan_per_creator=25,
                shorts_per_channel=args.shorts_per_channel,
                min_views=args.min_views,
                min_duration=args.min_duration,
                max_duration=args.max_duration,
                days=resolved_days,
                top_k=args.limit,
            )

        display_outliers(outliers)

        if not outliers:
            print("No outliers found to harvest.")
            return

        print(f"Ingesting {len(outliers)} outlier shorts into multimodal graph and pattern catalog ({args.workers} workers)...")
        agent = ShortsIntelligenceAgent(
            gemini_model=args.model,
            output_dir=args.output_dir,
        )
        harvested = harvest_outlier_candidates(
            candidates=outliers,
            agent=agent,
            output_dir=args.output_dir,
            workers=args.workers,
            auto_synthesize=True,
        )
        print(f"Outlier ingestion completed: {len(harvested)} videos analyzed.")
        return

    if args.harvest_channel:
        print(f"\nHarvesting top {args.limit} shorts from {args.harvest_channel}...")
        harvested = harvest_channel_shorts(
            channel_handle=args.harvest_channel,
            limit=args.limit,
            output_dir=args.output_dir,
            model_name=args.model,
        )
        print(f"Harvest completed: {len(harvested)} videos processed.")
        return

    if args.harvest_category:
        timeline_info = f" | Timeline: past {resolved_days} days" if resolved_days else ""
        print(f"\nStarting parallel category harvest for '{args.harvest_category}'{timeline_info}...")
        print(f"Category target: {args.category_target} videos | Max {args.shorts_per_channel} per channel | {args.workers} parallel workers")
        harvested = harvest_category_creators(
            category=args.harvest_category,
            shorts_per_channel=args.shorts_per_channel,
            category_target=args.category_target,
            min_views=args.min_views,
            min_duration=args.min_duration,
            max_duration=args.max_duration,
            days=resolved_days,
            workers=args.workers,
            output_dir=args.output_dir,
            model_name=args.model,
            auto_synthesize=True,
        )
        print(f"Category harvest completed: {len(harvested)} videos processed.")
        return

    if args.synthesize_patterns or args.rebuild_patterns:
        pattern_agent = PatternSynthesisAgent(
            gemini_model=args.model,
            catalog_path=args.catalog_path,
            director_context_path=args.director_context_path,
            data_dir=args.output_dir,
        )
        catalog = pattern_agent.synthesize(
            force_rebuild=args.rebuild_patterns,
            max_videos=args.pattern_limit,
        )
        display_catalog(catalog)
        return

    if args.render:
        manifest_path = Path(args.render)
        if not manifest_path.exists():
            print(f"[ERROR] Manifest file not found: {manifest_path}", file=sys.stderr)
            sys.exit(1)

        raw_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = DirectorResponseManifest.model_validate(raw_data)

        renderer = VideoGenerationAgent(
            model=args.model if ("omni" in args.model or "veo" in args.model) else os.environ.get("VIDEO_MODEL", "gemini-omni-1.1-flash-preview"),
            concurrency=args.render_concurrency,
        )

        final_path = renderer.render_manifest(
            manifest=manifest,
            resolution=args.render_resolution,
            first_frame_path=args.first_frame,
        )
        print(f"Render finished successfully: {final_path}")
        return

    if args.direct:
        input_content = args.direct.strip()
        if os.path.exists(input_content):
            input_content = Path(input_content).read_text(encoding="utf-8")

        director = DirectorAgent(
            gemini_model=args.model,
            catalog_path=args.catalog_path,
            output_dir=args.director_output_dir,
        )

        manifest = director.direct(
            script_or_idea=input_content,
            pattern_id=args.pattern_id,
            target_style_tags=parsed_style_tags,
            target_category=args.category,
            target_duration_sec=args.target_duration,
            save=not args.no_save,
        )

        display_director_manifest(manifest)

        if args.render_video:
            renderer = VideoGenerationAgent(
                model=args.model if ("omni" in args.model or "veo" in args.model) else os.environ.get("VIDEO_MODEL", "gemini-omni-1.1-flash-preview"),
                concurrency=args.render_concurrency,
            )
            final_path = renderer.render_manifest(
                manifest=manifest,
                resolution=args.render_resolution,
                first_frame_path=args.first_frame,
            )
            print(f"Render finished successfully: {final_path}")

        return

    target_url = args.url_or_id or "https://www.youtube.com/shorts/4K9LZrKWjxQ"

    if args.extract_audio:
        from tools.downloader_tool import download_short_audio
        target_path = Path(target_url)
        if target_path.is_file() and target_path.suffix.lower() == ".txt":
            raw_lines = [
                line.strip()
                for line in target_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if args.video_limit is not None and args.video_limit > 0:
                raw_lines = raw_lines[:args.video_limit]
            print(f"\nExtracting audio for {len(raw_lines)} video(s) into audio_exports/...")
            for idx, u in enumerate(raw_lines, start=1):
                try:
                    out = download_short_audio(u, output_dir="audio_exports")
                    print(f"[{idx}/{len(raw_lines)}] Extracted: {out}")
                except Exception as e:
                    print(f"[{idx}/{len(raw_lines)}] Failed for {u}: {e}")
            return
        else:
            try:
                out = download_short_audio(target_url, output_dir="audio_exports")
                print(f"\nAudio extracted successfully: {out}")
            except Exception as e:
                print(f"\nFailed to extract audio: {e}")
            return

    agent = ShortsIntelligenceAgent(
        gemini_model=args.model,
        output_dir=args.output_dir,
    )

    target_path = Path(target_url)
    if target_path.is_file() and target_path.suffix.lower() == ".txt":
        raw_lines = [
            line.strip()
            for line in target_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if raw_lines:
            total_available = len(raw_lines)
            if args.video_limit is not None and args.video_limit > 0:
                raw_lines = raw_lines[:args.video_limit]

            print(f"\nDiscovered {total_available} URL(s) in {target_url} (processing {len(raw_lines)})...")
            success_count = 0
            ingested_video_ids = []
            for idx, line_url in enumerate(raw_lines, start=1):
                print(f"\n[{idx}/{len(raw_lines)}] Analyzing {line_url}...")
                try:
                    analysis = agent.analyze(
                        url_or_id=line_url,
                        save=not args.no_save,
                        force_reanalyze=args.force_reanalyze,
                    )
                    print(f"  -> Successfully analyzed '{analysis.title}' (Virality: {analysis.virality_score:.2f}, Shots: {len(analysis.video_graph.nodes)})")
                    ingested_video_ids.append(analysis.video_id)
                    success_count += 1
                except Exception as e:
                    print(f"  -> Failed to analyze {line_url}: {e}")

            print(f"\nCompleted raw analysis for {success_count}/{len(raw_lines)} video(s). Saved to {args.output_dir}/.")

            if args.analyze_only:
                print("Skipping pattern synthesis (--analyze-only requested).")
                return

            print("Synthesizing pattern catalog from updated corpus...")
            pattern_agent = PatternSynthesisAgent(
                gemini_model=args.model,
                catalog_path=args.catalog_path,
                director_context_path=args.director_context_path,
                data_dir=args.output_dir,
            )
            catalog = pattern_agent.synthesize(
                force_rebuild=args.rebuild_patterns,
                video_ids=ingested_video_ids if not args.rebuild_patterns else None,
                max_videos=args.pattern_limit,
            )
            display_catalog(catalog)
            return

    try:
        analysis = agent.analyze(
            url_or_id=target_url,
            save=not args.no_save,
            force_reanalyze=args.force_reanalyze,
        )

        print("\n" + "=" * 60)
        print("           SHORTS ANALYSIS COMPLETED")
        print("=" * 60)
        print(f"Title:          {analysis.title}")
        print(f"Channel:        {analysis.channel}")
        print(f"Duration:       {analysis.duration_sec:.1f}s")
        print(f"Views:          {analysis.engagement.views:,}")
        print(f"Likes:          {analysis.engagement.likes:,}")
        print(f"Engagement:     {analysis.engagement.engagement_rate}%")
        print(f"Virality Score: {analysis.virality_score:.2f} / 1.00")
        print(f"Creator Setup:  {analysis.creator_setup.value.upper()}")
        if analysis.style_tags:
            print(f"Style Tags:     {', '.join(analysis.style_tags)}")
        print(f"Pacing:         {analysis.derived_features.cuts_per_10s} cuts / 10s")
        print(f"Total Shots:    {len(analysis.video_graph.nodes)}")
        print(f"Total Edges:    {len(analysis.video_graph.edges)}")
        print("-" * 60)
        print("Sample Shots (First 3):")
        for shot in analysis.video_graph.nodes[:3]:
            cam = f"{shot.camera.shot_size.value}/{shot.camera.movement.value}" if shot.camera else "n/a"
            print(
                f"  [{shot.timestamp_range.start_sec:4.1f}s - {shot.timestamp_range.end_sec:4.1f}s] "
                f"{shot.beat_name.value.upper():<7} | Cam: {cam:<10} | {shot.description[:45]}"
            )
        print("=" * 60 + "\n")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
