from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from corpus.pattern_schema import (
    AudiovisualRecipe,
    HookRecipe,
    PacingBenchmark,
    PatternCatalog,
    ViralPatternEntry,
    create_empty_catalog,
)
from corpus.schema import (
    BeatName,
    CameraMovement,
    CreatorSetup,
    HookType,
    ShortsAnalysis,
    ShotSize,
    ToneTag,
    VocalDelivery,
)

load_dotenv(override=True)
logger = logging.getLogger("PatternTools")


class PatternMatchDecision(BaseModel):
    is_match: bool
    matched_pattern_id: str | None = None
    relationship: Literal["same", "variant", "novel"] = "novel"
    match_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str
    suggested_guidelines_to_add: list[str] = Field(default_factory=list)


def get_genai_client(api_key: str | None = None, location: str | None = None) -> genai.Client:
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("true", "1")
    target_loc = location or os.getenv("GEMINI_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION") or "global"
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")

    resolved_key = (
        api_key
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("YOUTUBE_API_KEY")
    )

    if use_vertex:
        try:
            return genai.Client(
                location=target_loc,
                project=project,
            )
        except Exception as e:
            logger.warning("Failed initializing Vertex AI Client at location %s: %s. Checking fallback...", target_loc, e)
            if resolved_key:
                return genai.Client(api_key=resolved_key)
            raise

    if resolved_key:
        return genai.Client(api_key=resolved_key)

    if project:
        try:
            return genai.Client(
                location=target_loc,
                project=project,
            )
        except Exception:
            pass

    return genai.Client(location=target_loc)


def load_corpus_analyses(data_dir: str | Path = "corpus/data") -> list[ShortsAnalysis]:
    path = Path(data_dir)
    if not path.exists():
        return []

    analyses: list[ShortsAnalysis] = []
    for file_path in sorted(path.glob("*.json")):
        if file_path.name in ("pattern_catalog.json", "director_context.json"):
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
            analysis = ShortsAnalysis.model_validate_json(content)
            analyses.append(analysis)
        except Exception as e:
            logger.error("Failed to parse %s: %s", file_path, e)

    return analyses


def load_pattern_catalog(catalog_path: str | Path = "corpus/pattern_catalog.json") -> PatternCatalog:
    path = Path(catalog_path)
    if path.exists():
        content = ""
        try:
            content = path.read_text(encoding="utf-8")
            return PatternCatalog.model_validate_json(content)
        except Exception as e:
            logger.warning("Direct validation of catalog failed at %s: %s. Attempting fallback parse.", path, e)
            try:
                raw_data = json.loads(content)
                patterns_raw = raw_data.get("patterns", [])
                valid_patterns = []
                for p_dict in patterns_raw:
                    try:
                        valid_patterns.append(ViralPatternEntry.model_validate(p_dict))
                    except Exception as pe:
                        logger.warning("Skipping invalid pattern entry '%s': %s", p_dict.get("id"), pe)
                if valid_patterns:
                    logger.info("Rescued %d valid patterns from %s", len(valid_patterns), path)
                    cat = create_empty_catalog()
                    cat.catalog_version = raw_data.get("catalog_version", "1.0.0")
                    cat.patterns = valid_patterns
                    return cat
            except Exception as fe:
                logger.error("Fallback recovery failed for %s: %s", path, fe)

    return create_empty_catalog()


def save_pattern_catalog(
    catalog: PatternCatalog,
    catalog_path: str | Path = "corpus/pattern_catalog.json",
) -> None:
    path = Path(catalog_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    catalog.updated_at = datetime.now(timezone.utc)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(catalog.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def save_director_context(
    catalog: PatternCatalog,
    output_path: str | Path = "corpus/director_context.json",
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    director_data = catalog.to_director_context()
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(director_data, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def collapse_consecutive_elements(elements: list[Any]) -> list[Any]:
    collapsed = []
    for elem in elements:
        if not collapsed or collapsed[-1] != elem:
            collapsed.append(elem)
    return collapsed


def summarize_video_profile(video: ShortsAnalysis) -> dict[str, Any]:
    nodes = video.video_graph.nodes
    hook_nodes = nodes[: min(3, len(nodes))]

    opening_hooks = []
    for node in hook_nodes:
        cam_str = ""
        if node.camera:
            cam_str = f"{node.camera.shot_size.value}/{node.camera.movement.value}"
        opening_hooks.append(
            {
                "shot": node.event_id,
                "beat": node.beat_name.value,
                "hook_types": [h.value for h in node.hook_type],
                "description": node.description,
                "transcript": node.transcript,
                "ocr_text": node.ocr_text,
                "camera": cam_str,
            }
        )

    unique_cameras = list({node.camera.movement for node in nodes if node.camera})
    unique_framings = list({node.camera.shot_size for node in nodes if node.camera})
    unique_vocals = list(
        {
            node.speaker_telemetry.vocal_delivery
            for node in nodes
            if node.speaker_telemetry and node.speaker_telemetry.vocal_delivery
        }
    )

    sfx_collection = set()
    lighting_collection = set()
    for node in nodes:
        if node.audio_style and node.audio_style.sfx_tags:
            sfx_collection.update(node.audio_style.sfx_tags)
        if node.video_style and node.video_style.lighting:
            lighting_collection.add(str(node.video_style.lighting))

    raw_beats = [node.beat_name.value for node in nodes]
    macro_beats = collapse_consecutive_elements(raw_beats)

    return {
        "video_id": video.video_id,
        "title": video.title,
        "category": video.category,
        "creator_setup": video.creator_setup.value,
        "duration_sec": video.duration_sec,
        "views": video.engagement.views,
        "engagement_rate": video.engagement.calculated_engagement_rate,
        "tone_tags": [t.value for t in video.tone_tags],
        "style_tags": video.style_tags,
        "cuts_per_10s": video.derived_features.cuts_per_10s,
        "shot_count": video.derived_features.shot_count,
        "wpm": video.derived_features.wpm,
        "narrative_beat_sequence": macro_beats,
        "opening_hooks": opening_hooks,
        "camera_movements": [c.value for c in unique_cameras],
        "framings": [f.value for f in unique_framings],
        "vocal_deliveries": [str(v) for v in unique_vocals],
        "lighting_styles": list(lighting_collection),
        "sfx_tags": list(sfx_collection)[:8],
    }


def has_sufficient_structural_evidence(video: ShortsAnalysis) -> tuple[bool, str]:
    """Validates whether a video has enough structural depth to establish a new pattern archetype."""
    if video.duration_sec < 4.0:
        return False, f"Duration too short ({video.duration_sec:.1f}s < 4.0s)"

    nodes = video.video_graph.nodes
    if len(nodes) < 2:
        return False, f"Too few shots ({len(nodes)} < 2)"

    macro_beats = collapse_consecutive_elements([n.beat_name.value for n in nodes])
    if len(macro_beats) < 2:
        return False, f"Too few distinct macro beats ({len(macro_beats)} < 2)"

    return True, "Sufficient structural evidence"


def score_pattern_candidate(video_profile: dict[str, Any], pattern: ViralPatternEntry) -> float:
    """
    Modality-aware candidate scoring normalized over available features:
    S(V, P) = sum_{i in A} (w_i * s_i(V, P)) / sum_{i in A} w_i
    Only compares features present in both the video profile and the pattern archetype,
    preventing missing modalities from being penalized as genuine structural mismatches.
    """
    weighted_scores: list[float] = []
    total_weights: list[float] = []

    # 1. Creator Setup Match (Weight 3.0)
    v_setup = video_profile.get("creator_setup")
    if v_setup and pattern.creator_setup:
        w = 3.0
        s = 1.0 if v_setup == pattern.creator_setup.value else 0.0
        weighted_scores.append(w * s)
        total_weights.append(w)

    # 2. Category / Topic Overlap (Weight 2.0)
    v_cat = (video_profile.get("category") or "").strip().lower()
    if v_cat and (pattern.primary_category or pattern.source_categories):
        w = 2.0
        if pattern.primary_category and v_cat == pattern.primary_category.lower():
            s = 1.0
        elif any(v_cat == sc.lower() for sc in pattern.source_categories):
            s = 0.75
        else:
            s = 0.0
        weighted_scores.append(w * s)
        total_weights.append(w)

    # 3. Macro Beat Sequence Overlap (Weight 3.0) - only if both have at least 2 beats
    v_beats = {str(b).strip().upper() for b in video_profile.get("narrative_beat_sequence", [])}
    p_beats = {
        b.value.upper() if hasattr(b, "value") else str(b).strip().upper()
        for b in pattern.narrative_beat_sequence
    }
    if len(v_beats) >= 2 and len(p_beats) >= 2:
        w = 3.0
        s = len(v_beats & p_beats) / max(len(v_beats | p_beats), 1)
        weighted_scores.append(w * s)
        total_weights.append(w)

    # 4. Pacing Proximity (Weight 1.5) - only if pacing metrics exist
    v_cuts = float(video_profile.get("cuts_per_10s", 0.0))
    p_cuts = float(pattern.pacing_benchmarks.target_cuts_per_10s)
    if v_cuts > 0 and p_cuts > 0:
        w = 1.5
        delta = abs(v_cuts - p_cuts)
        s = max(0.0, 1.0 - (delta / 4.0))
        weighted_scores.append(w * s)
        total_weights.append(w)

    # 5. Tone Tags Overlap (Weight 1.0) - only if both have tone tags
    v_tones = set(video_profile.get("tone_tags", []))
    p_tones = {t.value for t in pattern.tone_tags}
    if v_tones and p_tones:
        w = 1.0
        s = len(v_tones & p_tones) / max(len(v_tones | p_tones), 1)
        weighted_scores.append(w * s)
        total_weights.append(w)

    # Require minimum comparable evidence (at least 2 modalities with sum of weights >= 3.0)
    if sum(total_weights) < 3.0:
        return 0.0

    return sum(weighted_scores) / sum(total_weights)


def filter_candidate_patterns(
    video: ShortsAnalysis | dict[str, Any],
    catalog: PatternCatalog,
    top_k: int = 5,
    min_score_threshold: float = 0.25,
) -> list[ViralPatternEntry]:
    """
    Deterministically shortlists candidate patterns most structurally similar to the candidate video.
    Includes fallback relaxation to ensure an overly strict filter never falsely asserts novelty.
    """
    if not catalog.patterns:
        return []

    profile = video if isinstance(video, dict) else summarize_video_profile(video)
    scored = [(score_pattern_candidate(profile, p), p) for p in catalog.patterns]
    scored.sort(key=lambda x: x[0], reverse=True)

    qualified = [p for score, p in scored if score >= min_score_threshold]
    if qualified:
        return qualified[:top_k]

    # Fallback relaxation 1: Positive scores
    relaxed = [p for score, p in scored if score > 0.0]
    if relaxed:
        return relaxed[:top_k]

    # Fallback relaxation 2: Top most popular patterns across any setup as comparative baselines
    top_by_freq = sorted(catalog.patterns, key=lambda p: (p.frequency, p.aggregate_views), reverse=True)
    return top_by_freq[:3]


def select_relevant_patterns(
    catalog: PatternCatalog,
    script_or_idea: str = "",
    target_category: str | None = None,
    target_style_tags: list[str] | None = None,
    preferred_pattern_id: str | None = None,
    max_patterns: int = 6,
) -> list[ViralPatternEntry]:
    """Selects the top patterns most relevant to the director brief and creative intent."""
    if not catalog.patterns:
        return []

    preferred = next((p for p in catalog.patterns if p.pattern_id == preferred_pattern_id), None)
    words = set(re.findall(r"\w+", (script_or_idea or "").lower()))
    target_cat = (target_category or "").lower()
    target_styles = {s.lower() for s in (target_style_tags or [])}

    scored: list[tuple[float, ViralPatternEntry]] = []
    for p in catalog.patterns:
        if preferred and p.pattern_id == preferred.pattern_id:
            continue
        score = 0.0
        # Category overlap
        if target_cat and (
            (p.primary_category and target_cat in p.primary_category.lower())
            or any(target_cat in sc.lower() for sc in p.source_categories)
        ):
            score += 4.0

        # Style tag overlap
        p_styles = {s.lower() for s in p.style_tags}
        if target_styles and p_styles:
            score += len(target_styles & p_styles) * 2.0

        # Semantic keywords in name, archetype, best use cases
        p_text = f"{p.name} {p.archetype} {' '.join(p.best_use_cases)} {p.hook_recipe.formula}".lower()
        keyword_hits = sum(1 for w in words if len(w) > 3 and w in p_text)
        score += min(keyword_hits * 1.5, 6.0)

        # Proven performance prior (capped so relevance beats raw views)
        score += min(p.frequency * 0.5, 2.0)
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [p for _, p in scored[:max_patterns]]
    if preferred:
        results.insert(0, preferred)
        results = results[:max_patterns]
    return results


def evaluate_pattern_match(
    video: ShortsAnalysis,
    catalog: PatternCatalog,
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
) -> PatternMatchDecision:
    if not catalog.patterns:
        return PatternMatchDecision(
            is_match=False,
            relationship="novel",
            match_confidence=1.0,
            reasoning="Catalog is empty. This is the foundational archetype.",
        )

    video_profile = summarize_video_profile(video)
    candidate_patterns = filter_candidate_patterns(video_profile, catalog, top_k=5)
    if not candidate_patterns:
        return PatternMatchDecision(
            is_match=False,
            relationship="novel",
            match_confidence=0.0,
            reasoning="No candidate patterns met pre-filter criteria.",
        )

    patterns_summary = []
    for p in candidate_patterns:
        patterns_summary.append(
            {
                "pattern_id": p.pattern_id,
                "name": p.name,
                "archetype": p.archetype,
                "primary_category": p.primary_category,
                "style_tags": p.style_tags,
                "creator_setup": p.creator_setup.value,
                "tone_tags": [t.value for t in p.tone_tags],
                "best_use_cases": p.best_use_cases,
                "hook_formula": p.hook_recipe.formula,
                "hook_types": [h.value for h in p.hook_recipe.hook_types],
                "narrative_beat_sequence": [b.value for b in p.narrative_beat_sequence],
                "pacing": {
                    "cuts_per_10s": p.pacing_benchmarks.target_cuts_per_10s,
                    "target_asl_sec": p.pacing_benchmarks.target_asl_sec,
                },
            }
        )

    prompt = f"""You are an executive short-form video director and viral format taxonomist.
Evaluate whether the candidate video belongs to one of the shortlisted viral pattern archetypes, or represents a distinct novel archetype.

CANDIDATE VIDEO:
{json.dumps(video_profile, indent=2)}

SHORTLISTED CANDIDATE PATTERNS:
{json.dumps(patterns_summary, indent=2)}

DECISION RULES:
1. relationship:
   - "same": Identical core structural archetype, hook formula, and narrative progression.
   - "variant": Shares the fundamental storytelling mechanic and pacing, but introduces minor stylistic or topic variation.
   - "novel": Fundamentally different creative sequence, hook mechanic, or production setup that requires its own master blueprint.
2. match_confidence: Float from 0.0 (uncertain/ambiguous) to 1.0 (highly certain) indicating your confidence in this classification (whether confirming a match or confirming that the video is genuinely novel).
3. If relationship is "same" or ("variant" with match_confidence >= 0.65):
   - Set is_match = true
   - Set matched_pattern_id to the matching pattern's id
   - Provide 1 to 3 concrete, actionable director guidelines observed in this candidate video.
4. If relationship is "novel":
   - Set is_match = false
   - Set matched_pattern_id = null
   - Set match_confidence to your certainty that this format is truly structurally novel (e.g. 0.85 - 0.95 if clearly distinct).
   - Explain why this format is structurally novel and distinct from all shortlisted patterns.
"""

    models_to_try = [model_name]

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 6):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=PatternMatchDecision,
                        temperature=0.1,
                    ),
                )
                if response and response.text:
                    decision = PatternMatchDecision.model_validate_json(response.text)
                    valid_ids = {p.pattern_id for p in candidate_patterns}
                    if decision.is_match and decision.matched_pattern_id in valid_ids and decision.match_confidence >= 0.65:
                        return decision

                    decision.is_match = False
                    decision.matched_pattern_id = None
                    return decision
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    parsed_delay = 0.0
                    m = re.search(r"retry in (\d+(?:\.\d+)?)s", err_msg) or re.search(r"'retryDelay':\s*'(\d+)s'", err_msg)
                    if m:
                        parsed_delay = float(m.group(1)) + 2.0
                    delay = max(15.0 * attempt, parsed_delay)
                    logger.warning("Rate limit / quota hit in match evaluation. Backing off for %.1fs (attempt %d/5)...", delay, attempt)
                    time.sleep(delay)
                else:
                    raise e

    raise RuntimeError(f"Pattern match evaluation failed: {last_error}")


def synthesize_novel_pattern(
    video: ShortsAnalysis,
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    existing_pattern_ids: set[str] | None = None,
) -> ViralPatternEntry:
    video_profile = summarize_video_profile(video)
    disallowed_ids = list(existing_pattern_ids or set())

    prompt = f"""You are an elite short-form video director.
Create a production-grade, generalized ViralPatternEntry blueprint from this top-performing video analysis.
This blueprint will serve as a master recipe for the Director Agent to produce future high-retention videos in this archetype.

SOURCE VIDEO PROFILE:
{json.dumps(video_profile, indent=2)}

DISALLOWED PATTERN IDS (already exist, do NOT duplicate):
{json.dumps(disallowed_ids)}

INSTRUCTIONS:
1. pattern_id: Unique, descriptive snake_case identifier reflecting the setup and format mechanic (e.g. 'pattern_contrarian_myth_bust_solo', 'pattern_rapid_qa_interview_duo', 'pattern_sensory_macro_reveal_solo').
2. name: Catchy, professional format name (e.g. 'Contrarian Myth-Bust Monologue', 'Sensory Macro Product Reveal').
3. archetype: Concise 1-2 sentence description of the storytelling mechanic and visual hook strategy.
4. creator_setup: Set to '{video.creator_setup.value}'.
5. tone_tags: Relevant emotional tones from [{', '.join(t.value for t in video.tone_tags)}].
6. best_use_cases: 2 to 4 concrete video types or topic genres best suited for this blueprint.
7. hook_recipe:
   - formula: The exact repeatable formula (e.g. 'Contrarian Statement + Shock Facial Reaction + Bold Kinetic Captions').
   - hook_types: Enum values matching the hook types used in the first 3 seconds.
   - first_3s_action: Specific physical and camera actions required in the first 3 seconds.
   - ocr_caption_style: Kinetic typography and overlay placement guidelines.
8. narrative_beat_sequence: Clean macro progression of narrative beats (e.g. [HOOK, PROBLEM, PROOF, TWIST, PAYOFF]). Do NOT repeat the same beat consecutively.
9. audiovisual_recipe:
   - camera_movement: Camera movements characteristic of this style.
   - framing: Shot sizes used.
   - lighting_and_grade: Lighting and color tone direction.
   - vocal_delivery: Vocal cadence and delivery styles.
   - target_wpm: Recommended words per minute.
   - music_and_sfx: Music mood, ducking, and sound effect timing.
10. pacing_benchmarks:
   - target_cuts_per_10s: Expected cut frequency.
   - target_asl_sec: Average shot length in seconds.
   - optimal_duration_range_sec: [min_seconds, max_seconds].
11. director_guidelines: 4 to 6 actionable, imperative directorial rules for shooting and editing this format.
12. adaptation_rules: 2 to 4 concrete rules for adapting this pattern across different video durations, subjects, or resource constraints.
"""

    models_to_try = [model_name]

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 6):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ViralPatternEntry,
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    entry = ViralPatternEntry.model_validate_json(response.text)
                    entry.frequency = 1
                    entry.source_video_ids = [video.video_id]
                    entry.creator_setup = video.creator_setup
                    entry.primary_category = video.category
                    entry.source_categories = [video.category]
                    entry.style_tags = list(video.style_tags)
                    entry.aggregate_views = video.engagement.views
                    entry.avg_engagement_rate = video.engagement.calculated_engagement_rate
                    entry.pacing_benchmarks.target_cuts_per_10s = video.derived_features.cuts_per_10s
                    shot_count = max(video.derived_features.shot_count, 1)
                    entry.pacing_benchmarks.target_asl_sec = round(video.duration_sec / shot_count, 2)
                    entry.pacing_benchmarks.optimal_duration_range_sec = [
                        round(max(video.duration_sec * 0.85, 5.0), 1),
                        round(video.duration_sec * 1.15, 1),
                    ]
                    if video.derived_features.wpm:
                        entry.audiovisual_recipe.target_wpm = video.derived_features.wpm

                    entry.narrative_beat_sequence = collapse_consecutive_elements(
                        entry.narrative_beat_sequence
                    )

                    for tag in video.tone_tags:
                        if tag not in entry.tone_tags:
                            entry.tone_tags.append(tag)

                    return entry
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    parsed_delay = 0.0
                    m = re.search(r"retry in (\d+(?:\.\d+)?)s", err_msg) or re.search(r"'retryDelay':\s*'(\d+)s'", err_msg)
                    if m:
                        parsed_delay = float(m.group(1)) + 2.0
                    delay = max(15.0 * attempt, parsed_delay)
                    logger.warning("Rate limit / quota hit in novel pattern synthesis. Backing off for %.1fs (attempt %d/5)...", delay, attempt)
                    time.sleep(delay)
                else:
                    raise e

    raise RuntimeError(f"Novel pattern synthesis failed: {last_error}")


def merge_video_into_pattern(
    pattern: ViralPatternEntry,
    video: ShortsAnalysis,
    suggested_guidelines: list[str] | None = None,
) -> ViralPatternEntry:
    if video.video_id in pattern.source_video_ids:
        return pattern

    pattern.source_video_ids.append(video.video_id)
    unique_sources = list(dict.fromkeys(pattern.source_video_ids))
    pattern.source_video_ids = unique_sources
    prev_frequency = pattern.frequency
    new_frequency = len(unique_sources)
    pattern.frequency = new_frequency

    if video.category and video.category not in pattern.source_categories:
        pattern.source_categories.append(video.category)

    for st in video.style_tags:
        if st not in pattern.style_tags:
            pattern.style_tags.append(st)

    pattern.aggregate_views += video.engagement.views

    video_eng = video.engagement.calculated_engagement_rate
    pattern.avg_engagement_rate = round(
        ((pattern.avg_engagement_rate * prev_frequency) + video_eng) / max(new_frequency, 1),
        2,
    )

    pacing = pattern.pacing_benchmarks
    pacing.target_cuts_per_10s = round(
        ((pacing.target_cuts_per_10s * prev_frequency) + video.derived_features.cuts_per_10s) / max(new_frequency, 1),
        2,
    )
    shot_count = max(video.derived_features.shot_count, 1)
    video_asl = round(video.duration_sec / shot_count, 2)
    pacing.target_asl_sec = round(
        ((pacing.target_asl_sec * prev_frequency) + video_asl) / max(new_frequency, 1),
        2,
    )
    current_min = pacing.optimal_duration_range_sec[0] if pacing.optimal_duration_range_sec else 5.0
    current_max = pacing.optimal_duration_range_sec[1] if len(pacing.optimal_duration_range_sec) > 1 else 60.0
    min_dur = min(current_min, round(max(video.duration_sec * 0.85, 5.0), 1))
    max_dur = max(current_max, round(video.duration_sec * 1.15, 1))
    pacing.optimal_duration_range_sec = [min_dur, max_dur]

    for tag in video.tone_tags:
        if tag not in pattern.tone_tags:
            pattern.tone_tags.append(tag)

    nodes = video.video_graph.nodes
    for node in nodes:
        if node.camera:
            if node.camera.movement not in pattern.audiovisual_recipe.camera_movement:
                pattern.audiovisual_recipe.camera_movement.append(node.camera.movement)
            if node.camera.shot_size not in pattern.audiovisual_recipe.framing:
                pattern.audiovisual_recipe.framing.append(node.camera.shot_size)
        if node.speaker_telemetry and node.speaker_telemetry.vocal_delivery:
            if node.speaker_telemetry.vocal_delivery not in pattern.audiovisual_recipe.vocal_delivery:
                pattern.audiovisual_recipe.vocal_delivery.append(node.speaker_telemetry.vocal_delivery)

    if video.derived_features.wpm:
        pattern.audiovisual_recipe.target_wpm = round(
            ((pattern.audiovisual_recipe.target_wpm * prev_frequency) + video.derived_features.wpm) / max(new_frequency, 1),
            1,
        )

    for node in nodes[: min(3, len(nodes))]:
        for h in node.hook_type:
            if h not in pattern.hook_recipe.hook_types:
                pattern.hook_recipe.hook_types.append(h)

    existing_guidelines_lower = {g.strip().lower() for g in pattern.director_guidelines}
    if suggested_guidelines:
        for g in suggested_guidelines:
            clean_g = g.strip()
            if clean_g and clean_g.lower() not in existing_guidelines_lower:
                if len(pattern.director_guidelines) < 8:
                    pattern.director_guidelines.append(clean_g)
                    existing_guidelines_lower.add(clean_g.lower())

    return pattern
