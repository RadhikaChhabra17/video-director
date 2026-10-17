#!/usr/bin/env python3
"""
Retrain and Refresh the Filmmaking Technique Library (corpus/technique_library.json)

Mines empirical evidence across all analyzed videos in `corpus/data/*.json`,
extracts camera mechanics, editing rhythms, sound design cues, and storytelling anchors,
calculates empirical evidence counts and exemplar associations, and saves the updated library.

Usage:
    python tools/retrain_technique_library.py
    python tools/retrain_technique_library.py --verbose
    python tools/retrain_technique_library.py --data-dir corpus/data --output corpus/technique_library.json
    python tools/retrain_technique_library.py --ai-discover
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set

# Ensure project root is in python path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from corpus.director_schema import TechniqueLibrary, TechniqueRecord
from tools.director_tools import (
    CANONICAL_TECHNIQUE_SEEDS,
    load_technique_library,
    save_technique_library,
    upsert_technique_record,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TechniqueRetrainer")

# Mapping to canonicalize legacy or duplicate technique IDs into unified standards
ID_ALIASES: Dict[str, str] = {
    "camera.push_in": "camera.motivated_push_in",
    "camera.pull_out": "camera.revealing_pull_out",
    "camera.whip_pan": "camera.kinetic_whip_pan",
    "camera.handheld_drift": "camera.kinetic_handheld_drift",
    "camera.pov_subjective": "camera.tactile_pov_action",
    "edit.match_cut": "editing.match_cut_action",
    "edit.j_cut_audio_lead": "editing.j_cut_audio_bridge",
    "edit.contrast_cut": "editing.contrast_scale_cut",
    "edit.jump_cut_cadence": "editing.jump_cut_cadence",
    "story.visual_motif": "visual_storytelling.recurring_ritual_anchor",
    "story.delayed_spatial_reveal": "editing.delayed_spatial_reveal",
    "story.isolated_subject": "visual_storytelling.lost_in_crowd_contrast",
    "sound.pre_reveal_silence": "sound_rhythm.pre_reveal_silence",
    "sound.syncopated_sfx_hit": "editing.sensory_slap_cut",
    "sound.riser_crescendo": "sound_rhythm.bpm_drop_surge",
}


def normalize_technique_id(tech_id: str) -> str:
    return ID_ALIASES.get(tech_id, tech_id)


def retrain_technique_library(
    data_dir: Path = BASE_DIR / "corpus" / "data",
    output_path: Path = BASE_DIR / "corpus" / "technique_library.json",
    reset_to_seeds: bool = False,
    ai_discover: bool = False,
    verbose: bool = False,
) -> TechniqueLibrary:
    """
    Retrains the technique library against the empirical corpus video graph dataset.
    """
    print("=" * 75)
    print("      RETRAINING TECHNIQUE LIBRARY (corpus/technique_library.json)")
    print("=" * 75)
    print(f"Dataset directory:   {data_dir}")
    print(f"Target library path: {output_path}")
    print(f"Reset to seeds:      {reset_to_seeds}")
    print(f"AI Discovery mode:   {ai_discover}")
    print("-" * 75)

    # 1. Initialize library from seeds or existing file
    if reset_to_seeds or not output_path.exists():
        logger.info("Initializing library fresh from canonical seeds...")
        library = TechniqueLibrary(version="2.0.0", techniques=[])
    else:
        logger.info("Loading existing technique library to merge and refresh...")
        library = load_technique_library(output_path)

    # Upsert all canonical seeds
    seed_records = [TechniqueRecord.model_validate(s) for s in CANONICAL_TECHNIQUE_SEEDS]
    for seed in seed_records:
        upsert_technique_record(library, seed)

    # 2. Deduplicate and normalize technique IDs in library
    consolidated_techniques: Dict[str, TechniqueRecord] = {}
    for tech in library.techniques:
        canonical_id = normalize_technique_id(tech.technique_id)
        if canonical_id not in consolidated_techniques:
            tech.technique_id = canonical_id
            consolidated_techniques[canonical_id] = tech
        else:
            # Merge variants and triggers
            existing = consolidated_techniques[canonical_id]
            existing.evidence_count = max(existing.evidence_count, tech.evidence_count)
            for k, v in tech.variants.items():
                if k not in existing.variants:
                    existing.variants[k] = v
            for u in tech.use_when:
                if u not in existing.use_when and len(existing.use_when) < 6:
                    existing.use_when.append(u)
            for a in tech.avoid_when:
                if a not in existing.avoid_when and len(existing.avoid_when) < 6:
                    existing.avoid_when.append(a)

    library.techniques = list(consolidated_techniques.values())
    logger.info("Base library ready with %d unique canonical techniques.", len(library.techniques))

    # 3. Mine empirical evidence across all corpus JSON graphs
    if not data_dir.exists():
        logger.warning("Corpus data directory %s does not exist. Saving base seeds.", data_dir)
        save_technique_library(library, output_path)
        return library

    json_files = sorted(list(data_dir.glob("*.json")))
    print(f"Scanning {len(json_files)} analyzed video corpus records for empirical telemetry...")

    counts: Dict[str, int] = {t.technique_id: 0 for t in library.techniques}
    exemplars_map: Dict[str, List[str]] = {t.technique_id: [] for t in library.techniques}

    processed_count = 0
    total_shots_analyzed = 0

    for idx, jf in enumerate(json_files, start=1):
        try:
            content = jf.read_text(encoding="utf-8")
            data = json.loads(content)
        except Exception as e:
            if verbose:
                logger.debug("Failed parsing %s: %s", jf.name, e)
            continue

        processed_count += 1
        video_id = data.get("video_id", jf.stem)
        graph = data.get("video_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        total_shots_analyzed += len(nodes)

        observed_in_video: Set[str] = set()

        for s_idx, node in enumerate(nodes):
            cam = node.get("camera") or {}
            movement = str(cam.get("movement", "")).lower()
            shot_size = str(cam.get("shot_size", "")).lower()

            vid_style = node.get("video_style") or {}
            format_name = str(vid_style.get("visual_format", "")).lower()
            tech_tags = [str(t).lower() for t in (node.get("technique_tags") or [])]
            hook_types = [str(h).lower() for h in (node.get("hook_type") or [])]

            audio = node.get("audio_style") or {}
            sfx = [str(s).lower() for s in (audio.get("sfx_tags") or [])]
            music_pres = str(audio.get("music_presence", "")).lower()

            speaker = node.get("speaker_telemetry") or {}
            on_cam = speaker.get("on_camera", False)
            action = str(speaker.get("action", "")).lower()

            # Rule 1: Motivated Push-In
            if movement in ("zoom", "dolly") or "punch_in" in tech_tags or "push_in" in tech_tags:
                counts["camera.motivated_push_in"] += 1
                observed_in_video.add("camera.motivated_push_in")

            # Rule 2: Revealing Pull-Out
            if movement in ("zoom", "dolly") and shot_size in ("w", "ew"):
                counts["camera.revealing_pull_out"] += 1
                observed_in_video.add("camera.revealing_pull_out")

            # Rule 3: Kinetic Whip Pan
            if movement in ("whip", "pan") or "whip_pan" in tech_tags:
                counts["camera.kinetic_whip_pan"] += 1
                observed_in_video.add("camera.kinetic_whip_pan")

            # Rule 4: Intimate Direct Close-Up
            if shot_size in ("cu", "mcu", "ecu") and on_cam:
                counts["camera.intimate_closeup"] += 1
                observed_in_video.add("camera.intimate_closeup")

            # Rule 5: Tactile POV Action
            if format_name in ("pov", "product_demo") or "macro_shot" in tech_tags:
                counts["camera.tactile_pov_action"] += 1
                observed_in_video.add("camera.tactile_pov_action")

            # Rule 6: Subject Tracking Stride
            if movement in ("tracking", "dolly") or "walking" in action:
                counts["camera.subject_tracking_stride"] += 1
                observed_in_video.add("camera.subject_tracking_stride")

            # Rule 7: Observational Static Wide
            if movement == "static" and shot_size in ("w", "ew"):
                counts["camera.observational_static_wide"] += 1
                observed_in_video.add("camera.observational_static_wide")

            # Rule 8: Dynamic Subject Orbit
            if movement == "orbit":
                counts["camera.dynamic_orbit"] += 1
                observed_in_video.add("camera.dynamic_orbit")

            # Rule 9: Sensory Slap Cut
            if any(s in sfx for s in ("whoosh", "pop", "thud", "boom", "crunch", "snap", "click", "hit")):
                counts["editing.sensory_slap_cut"] += 1
                observed_in_video.add("editing.sensory_slap_cut")

            # Rule 10: Pattern Interrupt Attention Reset
            if "pattern_interrupt" in hook_types or "interrupt" in tech_tags:
                counts["visual_storytelling.pattern_interrupt_reset"] += 1
                observed_in_video.add("visual_storytelling.pattern_interrupt_reset")

            # Rule 11: Subjective POV Discovery
            if "reaction" in tech_tags or "discovery" in tech_tags:
                counts["visual_storytelling.subjective_pov_discovery"] += 1
                observed_in_video.add("visual_storytelling.subjective_pov_discovery")

            # Rule 12: Acoustic Vocal Isolation
            if not audio.get("has_background_music", True) or music_pres in ("none", "low"):
                counts["sound_rhythm.acoustic_vocal_isolation"] += 1
                observed_in_video.add("sound_rhythm.acoustic_vocal_isolation")

            # Rule 13: Micro-Foley Punctuation
            if any(s in sfx for s in ("crunch", "click", "pop", "tap", "sizzle", "thud", "ding")):
                counts["sound_rhythm.micro_foley_punctuation"] += 1
                observed_in_video.add("sound_rhythm.micro_foley_punctuation")

            # Rule 14: Contrast Scale Cut
            if s_idx > 0:
                prev_node = nodes[s_idx - 1]
                prev_cam = prev_node.get("camera") or {}
                prev_size = str(prev_cam.get("shot_size", "")).lower()
                if (prev_size in ("cu", "ecu") and shot_size in ("w", "ew")) or (prev_size in ("w", "ew") and shot_size in ("cu", "ecu")):
                    counts["editing.contrast_scale_cut"] += 1
                    observed_in_video.add("editing.contrast_scale_cut")

        # Transitions & Edges
        for edge in edges:
            trans = edge.get("transition") or {}
            ttype = str(trans.get("type", "")).lower()
            rel = str(edge.get("relationship", "")).lower()

            if ttype == "jump_cut" or "jump" in ttype:
                counts["editing.jump_cut_cadence"] += 1
                observed_in_video.add("editing.jump_cut_cadence")

            if ttype == "whip_pan":
                counts["camera.kinetic_whip_pan"] += 1
                observed_in_video.add("camera.kinetic_whip_pan")

            if rel in ("anticipates", "elaborate") and trans.get("duration_ms", 0) > 0:
                counts["editing.j_cut_audio_bridge"] += 1
                observed_in_video.add("editing.j_cut_audio_bridge")

            if rel == "reinforces" or ttype == "match_cut":
                counts["editing.match_cut_action"] += 1
                observed_in_video.add("editing.match_cut_action")

        # Derived Video-Level Features
        derived = data.get("derived_features", {})
        if derived.get("loopability", 0.0) >= 0.5:
            counts["visual_storytelling.recurring_ritual_anchor"] += 1
            observed_in_video.add("visual_storytelling.recurring_ritual_anchor")

        if len(nodes) >= 6:
            counts["visual_storytelling.micro_payoff_breadcrumb"] += 1
            observed_in_video.add("visual_storytelling.micro_payoff_breadcrumb")

        if "calm" in data.get("tone_tags", []) and any(n.get("camera", {}).get("movement") == "static" for n in nodes):
            counts["visual_storytelling.lost_in_crowd_contrast"] += 1
            observed_in_video.add("visual_storytelling.lost_in_crowd_contrast")

        if any(n.get("audio_style", {}).get("music_presence") == "none" for n in nodes[:2]):
            counts["sound_rhythm.pre_reveal_silence"] += 1
            observed_in_video.add("sound_rhythm.pre_reveal_silence")

        if derived.get("has_music") and derived.get("bpm"):
            counts["sound_rhythm.bpm_drop_surge"] += 1
            observed_in_video.add("sound_rhythm.bpm_drop_surge")

        if any(n.get("video_style", {}).get("visual_format") == "b_roll" for n in nodes):
            counts["sound_rhythm.ambient_texture_layer"] += 1
            observed_in_video.add("sound_rhythm.ambient_texture_layer")

        for obs in observed_in_video:
            if obs in exemplars_map and len(exemplars_map[obs]) < 5:
                exemplars_map[obs].append(video_id)

    # 4. Optional AI Discovery of Emergent Techniques
    if ai_discover:
        print("\nQuerying Gemini to synthesize emergent filmmaking techniques from outlier corpus...")
        try:
            from tools.pattern_tools import get_genai_client
            client = get_genai_client()
            sample_analyses = []
            for jf in json_files[:25]:
                try:
                    d = json.loads(jf.read_text(encoding="utf-8"))
                    sample_analyses.append({
                        "video_id": d.get("video_id"),
                        "title": d.get("title"),
                        "virality_score": d.get("virality_score"),
                        "tone_tags": d.get("tone_tags"),
                        "style_tags": d.get("style_tags"),
                    })
                except Exception:
                    pass

            discovery_prompt = (
                f"You are a master cinema director analyzing short-form outlier videos.\n"
                f"Review these high-performing shorts metadata:\n{json.dumps(sample_analyses, indent=2)}\n\n"
                f"Identify 1-2 emergent, novel editing or camera techniques not commonly named in standard seed lists.\n"
                f"Return JSON adhering to TechniqueRecord format with keys: technique_id, name, category, core_mechanism, variants, use_when, avoid_when."
            )
            resp = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=discovery_prompt,
                config={"response_mime_type": "application/json"},
            )
            if resp and resp.text:
                new_tech_data = json.loads(resp.text)
                if isinstance(new_tech_data, list):
                    for item in new_tech_data:
                        rec = TechniqueRecord.model_validate(item)
                        upsert_technique_record(library, rec)
                        print(f"  + Discovered new technique via AI: {rec.name} ({rec.technique_id})")
                elif isinstance(new_tech_data, dict) and "technique_id" in new_tech_data:
                    rec = TechniqueRecord.model_validate(new_tech_data)
                    upsert_technique_record(library, rec)
                    print(f"  + Discovered new technique via AI: {rec.name} ({rec.technique_id})")
        except Exception as e:
            logger.warning("AI Discovery skipped or encountered an error: %s", e)

    # 5. Apply calculated empirical counts back to library
    for tech in library.techniques:
        c = counts.get(tech.technique_id, 0)
        if c > 0:
            tech.evidence_count = c

    # 6. Save updated library
    save_technique_library(library, output_path)

    # 7. Print summary breakdown
    print("\n" + "=" * 75)
    print("                     RETRAINING SUMMARY")
    print("=" * 75)
    print(f"Corpus Files Scanned:     {processed_count}")
    print(f"Total Video Shots Mined:  {total_shots_analyzed}")
    print(f"Total Active Techniques:  {len(library.techniques)}")
    print(f"Library Version:          {library.version}")
    print(f"Updated Library Saved To: {output_path}")
    print("-" * 75)

    by_category: Dict[str, List[TechniqueRecord]] = {}
    for t in library.techniques:
        by_category.setdefault(t.category, []).append(t)

    for cat_name, tech_list in sorted(by_category.items()):
        print(f"\n📂 [{cat_name.upper()}] ({len(tech_list)} techniques):")
        for t in sorted(tech_list, key=lambda x: x.evidence_count, reverse=True):
            ex_str = f" | Exemplars: {', '.join(exemplars_map.get(t.technique_id, [])[:3])}" if exemplars_map.get(t.technique_id) else ""
            print(f"   • {t.name:<34} ({t.technique_id:<42}) Evidence: {t.evidence_count:4d}{ex_str}")

    print("\n" + "=" * 75)
    print("Technique library retraining completed successfully.")
    print("=" * 75 + "\n")

    return library


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrain corpus/technique_library.json using empirical video graphs and telemetry"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=BASE_DIR / "corpus" / "data",
        help="Directory containing analyzed video JSON files (default: corpus/data)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR / "corpus" / "technique_library.json",
        help="Output destination path (default: corpus/technique_library.json)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset to base canonical seeds before retraining",
    )
    parser.add_argument(
        "--ai-discover",
        action="store_true",
        help="Use Gemini to discover new emergent techniques from outlier videos",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debugging logs",
    )

    args = parser.parse_args()

    retrain_technique_library(
        data_dir=args.data_dir,
        output_path=args.output,
        reset_to_seeds=args.reset,
        ai_discover=args.ai_discover,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()

