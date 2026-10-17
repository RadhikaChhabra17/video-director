from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("style_transfer")
BASE_DIR = Path(__file__).resolve().parent.parent


class HookMechanicsProfile(BaseModel):
    hook_type: List[str] = Field(default_factory=list)
    opening_action: str = ""
    text_overlay: Optional[str] = None
    transcript_snippet: Optional[str] = None
    duration_sec: float = 1.5
    visual_format: str = "b_roll"
    confidence: float = 0.9


class BeatProfile(BaseModel):
    beat_name: str
    duration_sec: float
    purpose: str
    shot_count: int
    asl_sec: float


class EditingRhythmProfile(BaseModel):
    cuts_per_10s: float
    total_shots: int
    total_duration_sec: float
    min_shot_duration_sec: float
    max_shot_duration_sec: float
    median_shot_duration_sec: float
    pacing_curve_description: str
    has_pacing_acceleration: bool = False


class VisualGrammarProfile(BaseModel):
    shot_size_distribution: Dict[str, float] = Field(default_factory=dict)
    camera_movement_distribution: Dict[str, float] = Field(default_factory=dict)
    visual_format_distribution: Dict[str, float] = Field(default_factory=dict)
    dominant_format: str = "b_roll"
    dominant_framing: str = "mcu"
    dominant_movement: str = "handheld"


class AudioDeliveryProfile(BaseModel):
    is_measured: bool = False
    wpm: Optional[float] = None
    vocal_delivery: Optional[str] = None
    music_presence: str = "unknown"
    music_mood: Optional[str] = None
    sfx_cues: List[str] = Field(default_factory=list)
    audio_notes: str = ""


class TransitionGrammarProfile(BaseModel):
    transition_types: Dict[str, int] = Field(default_factory=dict)
    dominant_transition: str = "jump_cut"
    total_transitions: int = 0
    trigger_notes: str = ""


class StyleTransferContract(BaseModel):
    reference_video_id: str
    reference_title: str
    pattern_id: Optional[str] = None
    pattern_name: Optional[str] = None
    is_catalog_pattern: bool = False

    # Three-Tier Contract
    must_preserve_invariants: List[str] = Field(default_factory=list)
    target_closely_styles: List[str] = Field(default_factory=list)
    adapt_freely_content: List[str] = Field(default_factory=list)
    must_avoid: List[str] = Field(default_factory=list)

    # Detailed Evidence
    hook_mechanics: HookMechanicsProfile = Field(default_factory=HookMechanicsProfile)
    narrative_beats: List[BeatProfile] = Field(default_factory=list)
    editing_rhythm: EditingRhythmProfile = Field(
        default_factory=lambda: EditingRhythmProfile(
            cuts_per_10s=3.0,
            total_shots=1,
            total_duration_sec=10.0,
            min_shot_duration_sec=1.5,
            max_shot_duration_sec=3.0,
            median_shot_duration_sec=2.2,
            pacing_curve_description="Uniform cut cadence",
        )
    )
    visual_grammar: VisualGrammarProfile = Field(default_factory=VisualGrammarProfile)
    audio_delivery: AudioDeliveryProfile = Field(default_factory=AudioDeliveryProfile)
    transition_grammar: TransitionGrammarProfile = Field(default_factory=TransitionGrammarProfile)

    # Creative Modifier
    creative_modifier: Optional[str] = None
    modifier_directives: List[str] = Field(default_factory=list)


def resolve_catalog_pattern_for_video(video_id: str) -> Optional[Dict[str, Any]]:
    """Checks if the video ID is in pattern_catalog.json or director_context.json."""
    catalog_path = BASE_DIR / "corpus" / "pattern_catalog.json"
    if catalog_path.exists():
        try:
            cat = json.loads(catalog_path.read_text(encoding="utf-8"))
            for p in cat.get("patterns", []):
                if video_id in p.get("source_video_ids", []):
                    return p
        except Exception as e:
            logger.warning(f"Error checking pattern_catalog.json: {e}")

    # Fallback to director_context.json
    context_path = BASE_DIR / "corpus" / "director_context.json"
    if context_path.exists():
        try:
            context_data = json.loads(context_path.read_text(encoding="utf-8"))
            for p in context_data:
                if video_id in p.get("exemplar_video_ids", []) or video_id in p.get("source_video_ids", []):
                    return p
        except Exception as e:
            logger.warning(f"Error checking director_context.json: {e}")

    return None


def load_video_analysis_data(video_id: str) -> Optional[Dict[str, Any]]:
    """Loads video analysis json from corpus/data, Firestore, or .cache/user_uploads."""
    try:
        from tools.storage_service import storage_service
        analysis = storage_service.get_analysis(video_id)
        if analysis:
            return analysis
    except Exception as e:
        logger.warning(f"Error checking storage_service for analysis {video_id}: {e}")

    p1 = BASE_DIR / "corpus" / "data" / f"{video_id}.json"
    if p1.exists():
        try:
            return json.loads(p1.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Check user uploads cache
    cache_uploads = BASE_DIR / ".cache" / "user_uploads"
    if cache_uploads.exists():
        for p in cache_uploads.glob(f"*{video_id}*.json"):
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass

    return None


def build_style_transfer_contract(
    video_data: Dict[str, Any],
    active_direction_tag: Optional[str] = None,
) -> StyleTransferContract:
    """Normalizes the analyzed video graph and pattern into a structured StyleTransferContract."""
    video_id = video_data.get("video_id", "reference_video")
    title = video_data.get("title", "Analyzed Video")
    total_duration = float(video_data.get("duration_sec", 10.0))
    video_graph = video_data.get("video_graph", {})
    nodes: List[Dict[str, Any]] = video_graph.get("nodes", [])
    edges: List[Dict[str, Any]] = video_graph.get("edges", [])
    derived = video_data.get("derived_features", {})

    # 1. Resolve Catalog Pattern
    matched_pattern = resolve_catalog_pattern_for_video(video_id)
    pattern_id = matched_pattern.get("pattern_id") if matched_pattern else None
    pattern_name = matched_pattern.get("name") if matched_pattern else None
    is_catalog_pattern = matched_pattern is not None

    # 2. Extract Hook Mechanics (First shot or shots starting before 1.5s)
    hook_shot = next((n for n in nodes if (n.get("timestamp_range") or {}).get("start_sec", 0.0) < 1.5), nodes[0] if nodes else {})
    hook_tr = hook_shot.get("timestamp_range", {})
    hook_duration = max(float(hook_tr.get("end_sec", 1.5)) - float(hook_tr.get("start_sec", 0.0)), 0.5)

    hook_mechanics = HookMechanicsProfile(
        hook_type=hook_shot.get("hook_type", ["visual_action", "curiosity"]),
        opening_action=hook_shot.get("description", "Direct opening action"),
        text_overlay=hook_shot.get("ocr_text") or (hook_shot.get("video_style") or {}).get("text_overlay_type"),
        transcript_snippet=hook_shot.get("transcript"),
        duration_sec=round(hook_duration, 2),
        visual_format=(hook_shot.get("video_style") or {}).get("visual_format", "b_roll"),
        confidence=0.95 if hook_shot.get("description") else 0.7,
    )

    # 3. Extract Narrative Beat Progression & Duration
    beat_profiles: List[BeatProfile] = []
    current_beat_name = None
    current_beat_shots = []

    for n in nodes:
        b_name = n.get("beat_name", "beat")
        if b_name != current_beat_name:
            if current_beat_name and current_beat_shots:
                b_dur = sum(
                    (s.get("timestamp_range") or {}).get("end_sec", 0.0) - (s.get("timestamp_range") or {}).get("start_sec", 0.0)
                    for s in current_beat_shots
                )
                beat_profiles.append(
                    BeatProfile(
                        beat_name=current_beat_name,
                        duration_sec=round(max(b_dur, 0.5), 1),
                        purpose=f"Narrative {current_beat_name} stage",
                        shot_count=len(current_beat_shots),
                        asl_sec=round(b_dur / max(len(current_beat_shots), 1), 2),
                    )
                )
            current_beat_name = b_name
            current_beat_shots = [n]
        else:
            current_beat_shots.append(n)

    if current_beat_name and current_beat_shots:
        b_dur = sum(
            (s.get("timestamp_range") or {}).get("end_sec", 0.0) - (s.get("timestamp_range") or {}).get("start_sec", 0.0)
            for s in current_beat_shots
        )
        beat_profiles.append(
            BeatProfile(
                beat_name=current_beat_name,
                duration_sec=round(max(b_dur, 0.5), 1),
                purpose=f"Narrative {current_beat_name} stage",
                shot_count=len(current_beat_shots),
                asl_sec=round(b_dur / max(len(current_beat_shots), 1), 2),
            )
        )

    # 4. Editing Rhythm & Pacing Curve
    durations = [
        max(float((n.get("timestamp_range") or {}).get("end_sec", 0.0)) - float((n.get("timestamp_range") or {}).get("start_sec", 0.0)), 0.3)
        for n in nodes
    ] or [2.0]
    total_shots = len(durations)
    cuts_per_10s = float(derived.get("cuts_per_10s") or (total_shots / max(total_duration / 10.0, 1.0)))

    min_dur = round(min(durations), 2)
    max_dur = round(max(durations), 2)
    sorted_durs = sorted(durations)
    median_dur = round(sorted_durs[len(sorted_durs) // 2], 2)

    # Detect pacing acceleration across the arc
    has_pacing_acceleration = False
    if len(durations) >= 4:
        first_half_asl = sum(durations[: len(durations) // 2]) / (len(durations) // 2)
        second_half_asl = sum(durations[len(durations) // 2 :]) / (len(durations) - len(durations) // 2)
        if first_half_asl > second_half_asl * 1.25:
            has_pacing_acceleration = True
            pacing_desc = f"Escalating rhythm: opens with deliberate setup ({first_half_asl:.1f}s/shot) and accelerates toward payoff ({second_half_asl:.1f}s/shot)."
        else:
            pacing_desc = f"Steady kinetic cadence averaging {median_dur:.1f}s per shot across timeline."
    else:
        pacing_desc = f"Even pacing with {cuts_per_10s:.1f} cuts per 10 seconds."

    editing_rhythm = EditingRhythmProfile(
        cuts_per_10s=round(cuts_per_10s, 2),
        total_shots=total_shots,
        total_duration_sec=round(total_duration, 1),
        min_shot_duration_sec=min_dur,
        max_shot_duration_sec=max_dur,
        median_shot_duration_sec=median_dur,
        pacing_curve_description=pacing_desc,
        has_pacing_acceleration=has_pacing_acceleration,
    )

    # 5. Visual Grammar & Format Ratios
    format_counts: Dict[str, int] = {}
    size_counts: Dict[str, int] = {}
    movement_counts: Dict[str, int] = {}

    for n in nodes:
        v_style = n.get("video_style") or {}
        fmt = v_style.get("visual_format", "b_roll")
        format_counts[fmt] = format_counts.get(fmt, 0) + 1

        cam = n.get("camera") or {}
        size = cam.get("shot_size", "m")
        size_counts[size] = size_counts.get(size, 0) + 1
        mov = cam.get("movement", "handheld")
        movement_counts[mov] = movement_counts.get(mov, 0) + 1

    total_n = max(total_shots, 1)
    format_dist = {k: round(v / total_n, 2) for k, v in format_counts.items()}
    size_dist = {k: round(v / total_n, 2) for k, v in size_counts.items()}
    mov_dist = {k: round(v / total_n, 2) for k, v in movement_counts.items()}

    dominant_fmt = max(format_counts, key=format_counts.get) if format_counts else "b_roll"
    dominant_sz = max(size_counts, key=size_counts.get) if size_counts else "m"
    dominant_mv = max(movement_counts, key=movement_counts.get) if movement_counts else "handheld"

    visual_grammar = VisualGrammarProfile(
        shot_size_distribution=size_dist,
        camera_movement_distribution=mov_dist,
        visual_format_distribution=format_dist,
        dominant_format=dominant_fmt,
        dominant_framing=dominant_sz,
        dominant_movement=dominant_mv,
    )

    # 6. Audio Delivery Profile (Explicitly ground measured vs unknown)
    measured_wpms = [
        (n.get("speaker_telemetry") or {}).get("wpm")
        for n in nodes
        if (n.get("speaker_telemetry") or {}).get("wpm") is not None
    ]
    avg_wpm = round(sum(measured_wpms) / len(measured_wpms), 1) if measured_wpms else None
    is_wpm_measured = avg_wpm is not None

    vocal_deliveries = [
        (n.get("speaker_telemetry") or {}).get("vocal_delivery")
        for n in nodes
        if (n.get("speaker_telemetry") or {}).get("vocal_delivery")
    ]
    dominant_delivery = vocal_deliveries[0] if vocal_deliveries else None

    # Audio Style
    audio_nodes = [n.get("audio_style") for n in nodes if n.get("audio_style")]
    has_music = any(a.get("has_background_music") for a in audio_nodes)
    music_mood = next((a.get("music_mood") for a in audio_nodes if a.get("music_mood")), None)
    music_presence = "background" if has_music else "none" if audio_nodes else "unknown"

    all_sfx: List[str] = []
    for a in audio_nodes:
        all_sfx.extend(a.get("sfx_tags", []))
    unique_sfx = list(set(all_sfx))[:4]

    audio_notes = (
        f"Measured vocal pace ~{avg_wpm} WPM ({dominant_delivery or 'conversational'})."
        if is_wpm_measured
        else "Audio telemetry was not explicitly measured in reference; adapt vocal cadence naturally."
    )

    audio_delivery = AudioDeliveryProfile(
        is_measured=is_wpm_measured,
        wpm=avg_wpm,
        vocal_delivery=dominant_delivery,
        music_presence=music_presence,
        music_mood=music_mood,
        sfx_cues=unique_sfx,
        audio_notes=audio_notes,
    )

    # 7. Transition Grammar Profile
    transition_counts: Dict[str, int] = {}
    for e in edges:
        trans = (e.get("transition") or {}).get("type", "jump_cut")
        transition_counts[trans] = transition_counts.get(trans, 0) + 1

    dom_trans = max(transition_counts, key=transition_counts.get) if transition_counts else "jump_cut"
    transition_grammar = TransitionGrammarProfile(
        transition_types=transition_counts,
        dominant_transition=dom_trans,
        total_transitions=len(edges),
        trigger_notes=f"Mainly {dom_trans} transitions motivated by narrative action reveals.",
    )

    # 8. Synthesize Three-Tier Contract Rules
    # MUST PRESERVE
    must_preserve = [
        f"Open with immediate physical action & curiosity mechanism before {min(hook_duration, 1.5):.1f}s (Reference archetype: {', '.join(hook_mechanics.hook_type)}).",
        f"Follow macro-beat progression: {' -> '.join([b.beat_name for b in beat_profiles])}.",
        f"Target total duration within range {max(total_duration - 4.0, 10.0):.0f}s - {total_duration + 4.0:.0f}s.",
    ]
    if has_pacing_acceleration:
        must_preserve.append("Maintain pacing acceleration: tighten shot durations as story approaches narrative payoff.")

    # TARGET CLOSELY
    target_closely = [
        f"Target cutting velocity near {cuts_per_10s:.1f} cuts per 10s (~{total_shots} shots).",
        f"Visual format mix: {dominant_fmt.replace('_', ' ').title()} emphasis ({int(format_dist.get(dominant_fmt, 0.7) * 100)}%), framed primarily in {dominant_sz.upper()} with {dominant_mv} camera.",
    ]
    if is_wpm_measured:
        target_closely.append(f"Target vocal delivery near {avg_wpm:.0f} WPM with {dominant_delivery or 'conversational'} energy.")
    if unique_sfx:
        target_closely.append(f"Sonic punctuation: place SFX ({', '.join(unique_sfx)}) on major transition and reveal cuts.")

    # ADAPT FREELY
    adapt_freely = [
        "Translate all literal subject matter, props, physical materials, and dialogue to the user's specific story topic.",
        "Adapt exact shot count proportionally if the user brief requires specific educational explanations or step counts.",
        "Adapt dialogue line lengths and script wording naturally to preserve authentic creator voice.",
    ]

    # MUST AVOID
    must_avoid = [
        f"Do NOT copy literal dialogue, props, or distinctive scene elements from the reference ('{title}').",
        "Do NOT introduce visual dead zones (> 3.5s continuous static framing without action or cut).",
        "Do NOT force sound effects or unmotivated whip transitions where the user's story does not warrant them.",
    ]

    # 9. Creative Overrides (active_direction_tag)
    modifier_directives: List[str] = []
    if active_direction_tag:
        tag_lower = active_direction_tag.lower()
        if "faster" in tag_lower or "tempo" in tag_lower:
            modifier_directives = [
                "Tighten all pauses: increase target cutting velocity by ~20% without dropping required narrative beats.",
                "Prioritize jump cuts and eliminate dialogue breath pauses.",
            ]
        elif "personal" in tag_lower or "raw" in tag_lower or "unfiltered" in tag_lower:
            modifier_directives = [
                "Increase direct-to-camera intimate reaction shots and candid vocal reflections.",
                "Strip overly polished background music; rely on authentic room tone and ambient acoustic cues.",
            ]
        elif "funny" in tag_lower or "humor" in tag_lower:
            modifier_directives = [
                "Add micro-beat pause (0.5s freeze/reaction) immediately following comedic moments before cutting.",
                "Use sudden snap zooms or deadpan reaction framing on unexpected reveals.",
            ]
        elif "cinematic" in tag_lower or "documentary" in tag_lower:
            modifier_directives = [
                "Prioritize deliberate wide establishing shots and slower tracking/panning camera moves.",
                "Atmospheric sound design with evocative ambient score.",
            ]
        else:
            modifier_directives = [
                f"Apply tone modifier: '{active_direction_tag}'. Blend this stylistic flavor while preserving the macro-beat structure.",
            ]

    return StyleTransferContract(
        reference_video_id=video_id,
        reference_title=title,
        pattern_id=pattern_id,
        pattern_name=pattern_name,
        is_catalog_pattern=is_catalog_pattern,
        must_preserve_invariants=must_preserve,
        target_closely_styles=target_closely,
        adapt_freely_content=adapt_freely,
        must_avoid=must_avoid,
        hook_mechanics=hook_mechanics,
        narrative_beats=beat_profiles,
        editing_rhythm=editing_rhythm,
        visual_grammar=visual_grammar,
        audio_delivery=audio_delivery,
        transition_grammar=transition_grammar,
        creative_modifier=active_direction_tag,
        modifier_directives=modifier_directives,
    )


def format_style_transfer_contract_for_prompt(contract: StyleTransferContract) -> str:
    """Renders the StyleTransferContract into a markdown brief for DirectorAgent."""
    beats_str = " -> ".join([b.beat_name for b in contract.narrative_beats]) or "Hook -> Context -> Payoff"

    modifier_block = ""
    if contract.creative_modifier:
        directives_str = "\n".join([f"  - {d}" for d in contract.modifier_directives])
        modifier_block = f"""
### CREATIVE MODIFIER OVERRIDE: [{contract.creative_modifier}]
Precedence Rule: This creative modifier modifies stylistic pacing/tone, but CANNOT violate Must Preserve invariants.
{directives_str}
"""

    return f"""======================================================================
STYLE-TRANSFER CONTRACT (Grounded in Reference: "{contract.reference_title}")
Pattern Archetype: {contract.pattern_name or contract.pattern_id or "Ad-hoc Deconstructed Blueprint"}
======================================================================

1. MUST PRESERVE — STRUCTURAL INVARIANTS:
{chr(10).join([f"   - {r}" for r in contract.must_preserve_invariants])}

2. TARGET CLOSELY — STYLISTIC TARGETS (Flexibility: Adaptable as needed for topic):
{chr(10).join([f"   - {r}" for r in contract.target_closely_styles])}

3. ADAPT FREELY — CONTENT & CREATIVE VOCABULARY:
{chr(10).join([f"   - {r}" for r in contract.adapt_freely_content])}

4. AUDIO & SONIC DELIVERY DIRECTIVE:
   - Status: {"MEASURED REFERENCE TELEMETRY" if contract.audio_delivery.is_measured else "ESTIMATED / NOT MEASURED IN REFERENCE"}
   - Target Cadence: {f"{contract.audio_delivery.wpm:.0f} WPM ({contract.audio_delivery.vocal_delivery or 'conversational'})" if contract.audio_delivery.is_measured else "Adapt vocal cadence naturally to user script"}
   - Background Music: {contract.audio_delivery.music_presence} (Mood: {contract.audio_delivery.music_mood or 'Dynamic/Unobtrusive'})
   - Sonic SFX: {', '.join(contract.audio_delivery.sfx_cues) if contract.audio_delivery.sfx_cues else "Punctuate significant narrative turns"}

5. NARRATIVE BEAT SKELETON:
   Sequence: {beats_str}
   Pacing Curve: {contract.editing_rhythm.pacing_curve_description}

6. MUST AVOID (Strict Exclusions):
{chr(10).join([f"   - {r}" for r in contract.must_avoid])}
{modifier_block}
======================================================================"""


if __name__ == "__main__":
    test_id = "0DO9s5S2bSw"
    sample_data = load_video_analysis_data(test_id)
    if sample_data:
        contract = build_style_transfer_contract(sample_data, active_direction_tag="Faster tempo")
        print("Reference Video ID:", contract.reference_video_id)
        print("Pattern ID:", contract.pattern_id)
        print("Is Catalog Pattern:", contract.is_catalog_pattern)
        print("Cuts per 10s:", contract.editing_rhythm.cuts_per_10s)
        print("Pacing Acceleration:", contract.editing_rhythm.has_pacing_acceleration)
        print("Audio Measured:", contract.audio_delivery.is_measured)
        print("\n--- FORMATTED STYLE TRANSFER CONTRACT ---")
        print(format_style_transfer_contract_for_prompt(contract))
    else:
        print("Could not load sample video data.")

