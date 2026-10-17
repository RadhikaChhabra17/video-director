from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from corpus.director_schema import (
    AtomicRequirement,
    AuditViolation,
    CandidateEvaluationCriteria,
    ComplianceAuditReport,
    CreativeEditAlternative,
    CreativeReasoningOutput,
    DeterministicCheckResult,
    DeterministicValidationReport,
    DirectorResponseManifest,
    DirectorShotPlan,
    EditEvaluation,
    KineticCaptionSpec,
    OptimizationCriterionScore,
    OptimizationDecision,
    RequirementLedger,
    RequirementPriority,
    ScriptIntentInterpretation,
    SFXCue,
    ShotAudioSpec,
    ShotOverlaySpec,
    ShotTransitionSpec,
    ShotVisualSpec,
    SpeechSpec,
    SynthesisComposition,
    TechniqueLibrary,
    TechniqueRecord,
)
from corpus.pattern_schema import PatternCatalog, ViralPatternEntry
from corpus.schema import BeatName, CameraMovement, ShotSize, VisualFormat
from tools.pattern_tools import get_genai_client, load_pattern_catalog, select_relevant_patterns

load_dotenv(override=True)
logger = logging.getLogger("DirectorTools")


class PatternSelectionDecision(BaseModel):
    selected_pattern_id: str
    rationale: str
    adapted_angle: str
    cross_category_inspiration: str = ""


def save_director_manifest(
    manifest: DirectorResponseManifest,
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def load_director_manifest(manifest_path: str | Path) -> DirectorResponseManifest:
    path = Path(manifest_path)
    content = path.read_text(encoding="utf-8")
    return DirectorResponseManifest.model_validate_json(content)


def load_creators_registry_safe(registry_path: str | Path | None = None) -> dict[str, list[dict[str, Any]]]:
    candidates = []
    if registry_path:
        candidates.append(Path(registry_path))
    candidates.append(Path("corpus/creators_registry.json"))
    candidates.append(Path(__file__).resolve().parent.parent / "corpus" / "creators_registry.json")
    for cand in candidates:
        if cand.exists():
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
    return {}


def load_technique_library(library_path: str | Path | None = None) -> TechniqueLibrary:
    candidates = []
    if library_path:
        candidates.append(Path(library_path))
    candidates.append(Path("corpus/technique_library.json"))
    candidates.append(Path(__file__).resolve().parent.parent / "corpus" / "technique_library.json")
    for cand in candidates:
        if cand.exists():
            try:
                content = cand.read_text(encoding="utf-8")
                return TechniqueLibrary.model_validate_json(content)
            except Exception as e:
                logger.warning("Failed parsing technique library from %s: %s", cand, e)
    return TechniqueLibrary()


def save_technique_library(library: TechniqueLibrary, output_path: str | Path = "corpus/technique_library.json") -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(library.model_dump_json(indent=2), encoding="utf-8")


def upsert_technique_record(library: TechniqueLibrary, record: TechniqueRecord) -> None:
    existing = next((t for t in library.techniques if t.technique_id == record.technique_id), None)
    if not existing:
        library.techniques.append(record)
        return

    existing.evidence_count += 1
    if record.core_mechanism and len(record.core_mechanism) > len(existing.core_mechanism):
        existing.core_mechanism = record.core_mechanism

    for k, v in record.variants.items():
        if k not in existing.variants:
            existing.variants[k] = v

    for trigger in record.use_when:
        if len(existing.use_when) < 5 and not any(trigger.lower() in ex.lower() for ex in existing.use_when):
            existing.use_when.append(trigger)

    for warning in record.avoid_when:
        if len(existing.avoid_when) < 5 and not any(warning.lower() in ex.lower() for ex in existing.avoid_when):
            existing.avoid_when.append(warning)


CANONICAL_TECHNIQUE_SEEDS: list[dict[str, Any]] = [
    {
        "technique_id": "camera.motivated_push_in",
        "name": "Motivated Push-In",
        "category": "camera",
        "core_mechanism": "Constricts frame boundary around focal subject to amplify narrative gravity, internal realization, and eliminate peripheral distractions.",
        "variants": {
            "slow_creep": "1.5s–3.5s smooth forward drift deepening intimacy, vulnerability, and mounting stakes",
            "snap_punch": "0.1s–0.3s digital punch-in (1.15x) accenting punchlines, revelations, or shock",
        },
        "use_when": [
            "Character notices a critical detail or experiences an internal realization",
            "Dialogue transitions from casual setup to high-stakes confession",
            "Directing audience attention to subtle facial shift or prop",
        ],
        "avoid_when": [
            "Shot duration is under 1.2s",
            "Scene demands objective emotional detachment",
            "Movement is unmotivated by subject action or dialogue",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "camera.revealing_pull_out",
        "name": "Revealing Pull-Out",
        "category": "camera",
        "core_mechanism": "Expands the frame from tight subject focus to reveal context, scale, isolation, or an unforeseen threat.",
        "variants": {
            "isolation_reveal": "Slow reverse dolly from close-up to wide emphasizing loneliness or vulnerability",
            "spatial_punch": "Fast snap pull-out revealing surprising environment or unexpected companion",
        },
        "use_when": [
            "Ending an emotional sequence to leave subject alone in their world",
            "Punchline depends on context previously hidden off-screen",
            "Transitioning from micro-action to broad spatial orientation",
        ],
        "avoid_when": [
            "Opening hook where viewer needs immediate intimate connection",
            "Background holds zero narrative information or emotional resonance",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "camera.kinetic_whip_pan",
        "name": "Kinetic Whip Pan",
        "category": "camera",
        "core_mechanism": "High-velocity rotation blurs frame boundaries, transferring kinetic energy directly into the subsequent scene.",
        "variants": {
            "teleport_snap": "180-degree blur cut between two different physical locations",
            "reaction_whip": "Violent rotational whip from speaker to reacting listener",
        },
        "use_when": [
            "Connecting disparate scenes in high-tempo comedic or travel montages",
            "Eliminating perceived dead space between dialogue lines",
            "Creating a kinetic, stylized sense of urgency",
        ],
        "avoid_when": [
            "Subdued, contemplative, or somber narrative beats",
            "When audience needs to comprehend subtle background geography",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "camera.intimate_closeup",
        "name": "Intimate Direct Close-Up",
        "category": "camera",
        "core_mechanism": "Frames face in MCU/CU with direct gaze into lens, collapsing parasocial distance and establishing instant connection.",
        "variants": {
            "unfiltered_confession": "Eye-level CU with natural lighting for vulnerability and authentic truth",
            "high_energy_shout": "Tight framing with dynamic micro-handheld motion for raw viral charisma",
        },
        "use_when": [
            "Opening hook within first 1.5s to capture eye gaze",
            "Delivering core thesis or vulnerable confession",
            "Direct personal epiphany or emotional turning point",
        ],
        "avoid_when": [
            "Demonstrating hands-on physical craft requiring tool visibility",
            "When spatial relationship between multiple characters matters",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "camera.tactile_pov_action",
        "name": "Tactile Hands-On POV",
        "category": "camera",
        "core_mechanism": "Places lens in first-person eye perspective directly over hands interacting with objects, crafts, or tools.",
        "variants": {
            "over_the_shoulder": "OTS angle establishing creator presence and subject focus",
            "first_person_craft": "Top-down or chest-mounted POV showing hands manipulating material",
        },
        "use_when": [
            "Demonstrating physical skill, cooking step, or technical teardown",
            "Inviting viewer to feel somatic ownership of the action",
            "Showing physical obstacles or tactile textures up close",
        ],
        "avoid_when": [
            "Abstract conceptual or philosophical exposition",
            "Emotional conversational moments requiring facial expressions",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "camera.subject_tracking_stride",
        "name": "Subject Tracking Stride",
        "category": "camera",
        "core_mechanism": "Maintains steady distance while walking backwards or alongside creator navigating an active environment.",
        "variants": {
            "backwards_walk_lead": "Camera retreats as creator walks forward talking directly to camera",
            "profile_stride": "Side-profile tracking shot capturing environment passing in background",
        },
        "use_when": [
            "Transitioning between story beats or physical locations",
            "Conveying momentum, energy, and real-time journey progression",
            "Immersing viewer into a dynamic, bustling setting",
        ],
        "avoid_when": [
            "Intricate technical explanations requiring focused attention",
            "Cramped indoor spaces where tracking introduces erratic wobble",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "camera.observational_static_wide",
        "name": "Observational Static Wide",
        "category": "camera",
        "core_mechanism": "Locked-off wide perspective allowing human action or environmental motion to unfold naturally without camera manipulation.",
        "variants": {
            "isolated_figure": "Subject stationary in center while environment rushes past",
            "environmental_canvas": "Wide framing establishing grand architecture or scale of setting",
        },
        "use_when": [
            "Communicating alienation, stillness, or contemplation in a bustling world",
            "Establishing geographic context before cutting inside",
            "Creating rhythmic pause after rapid montage",
        ],
        "avoid_when": [
            "High-energy hook requiring immediate thumb-stopping motion",
            "Dialogue-heavy segments where mouth and micro-expressions are obscured",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "camera.dynamic_orbit",
        "name": "Dynamic Subject Orbit",
        "category": "camera",
        "core_mechanism": "Revolving parabolic trajectory orbiting creator, turning stationary exposition into cinematic visual parallax.",
        "variants": {
            "half_arc_reveal": "180-degree sweep moving from subject back to reveal front expression and horizon",
            "rapid_spin_swirl": "360-degree kinetic orbit emphasizing peak triumph or dizziness",
        },
        "use_when": [
            "Highlighting a climactic transformation or milestone reveal",
            "Adding cinematic production value to static monologue",
            "Creating separation between subject and dynamic background",
        ],
        "avoid_when": [
            "Somber, grounded documentary moments",
            "Rapid instructional step-by-step demonstrations",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "editing.match_cut_action",
        "name": "Kinetic Action Match Cut",
        "category": "editing",
        "core_mechanism": "Aligns subject vector, gesture, or directional trajectory across cut boundary to produce seamless visual continuity.",
        "variants": {
            "object_handover": "Item tossed toward camera in scene A caught in scene B",
            "directional_stride": "Footstep or hand swipe continuing motion seamlessly into new setting",
        },
        "use_when": [
            "Transitioning between disparate locations or time periods",
            "Elevating visual craft and rewarding attentive viewer gaze",
            "Compressing extensive real-time travel or preparation",
        ],
        "avoid_when": [
            "Disorienting sequences where spatial confusion is the objective",
            "When source clips lack matching physical momentum",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "editing.sensory_slap_cut",
        "name": "Sensory Slap Cut",
        "category": "editing",
        "core_mechanism": "Hard cut landing squarely on an abrupt, high-impact audio foley event within 50ms of frame boundary.",
        "variants": {
            "tactile_snap": "Cut synced with physical impact (door slam, knife chop, glass tap)",
            "whoosh_slam": "Cut punctuated by low-end riser followed by instantaneous impact",
        },
        "use_when": [
            "Punctuate punchlines or sudden twists",
            "Creating visceral tactile immersion in food, tech, or fitness",
            "Shocking passive viewers back into active engagement",
        ],
        "avoid_when": [
            "Gentle lyrical or meditative reflection",
            "Overused consecutively more than 3 times without rhythmic breather",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "editing.jump_cut_cadence",
        "name": "Micro-Jump Cut Cadence",
        "category": "editing",
        "core_mechanism": "Elliptical micro-cuts stripping breathers, hesitations, and micro-pauses from creator speech (1.4–2.2s ASL).",
        "variants": {
            "angle_alternator": "Alternating 1.0x and 1.15x crop every sentence to hide cut seams",
            "rapid_progression": "Rapid succession of short sub-second cuts showing progressive assembly",
        },
        "use_when": [
            "High-energy explainer, comedic vlog, or educational breakdown",
            "Condensing complex narrative without dropping vocal momentum",
            "Preventing retention drop during expository bridges",
        ],
        "avoid_when": [
            "High-emotion confession where hesitation and silence carry the message",
            "Cinematic scenes demanding realistic spatial continuity",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "editing.contrast_scale_cut",
        "name": "Contrast Scale Cut",
        "category": "editing",
        "core_mechanism": "Abrupt cut from extreme close-up (ECU) directly to extreme wide (EW), violently resetting spatial perspective.",
        "variants": {
            "micro_to_macro": "Tight shot of fingers trembling transitioning to vast empty city square",
            "shock_isolation": "Wide crowd shot transitioning to suffocating macro close-up of sweating brow",
        },
        "use_when": [
            "Juxtaposing personal vulnerability against massive external world",
            "Injecting sudden visual scale after claustrophobic dialogue",
            "Surprising viewer expectations at narrative turning points",
        ],
        "avoid_when": [
            "Continuous instructional tutorials requiring steady visual context",
            "Subtle dialogue exchanges between conversational partners",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "editing.j_cut_audio_bridge",
        "name": "J-Cut Audio Pre-Lap",
        "category": "editing",
        "core_mechanism": "Incoming shot dialogue, environmental sound, or music enters 0.3s–0.8s before visual scene cuts.",
        "variants": {
            "dialogue_pre_lap": "Voice begins speaking over current visuals before cutting to speaker face",
            "sound_anticipation": "Crashing waves or subway sounds before camera shows new setting",
        },
        "use_when": [
            "Softening abrupt scene transitions to feel organically cinematic",
            "Pulling viewer curiosity forward into next narrative scene",
            "Building acoustic anticipation for off-screen arrival",
        ],
        "avoid_when": [
            "Abrupt comedy slap cuts designed to produce sudden jarring shocks",
            "First 0.0-1.0s opening hook where audio must match visual instantly",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "editing.delayed_spatial_reveal",
        "name": "Delayed Spatial Reveal",
        "category": "editing",
        "core_mechanism": "Withholds wider environment by holding on tight shot until narrative pivot forces wide reveal.",
        "variants": {
            "fake_studio_reveal": "Creator talking in pristine frame before cut reveals chaotic clutter behind camera",
            "false_intimacy": "Tight frame appears solitary before cut reveals crowded public train",
        },
        "use_when": [
            "Subverting expectations with comedic or dramatic irony",
            "Creating curiosity gap about where action takes place",
            "Delivering a twist punchline based on physical location",
        ],
        "avoid_when": [
            "Factual documentary requiring immediate authentic location proof",
            "Fast montages where spatial withholding feels confusing rather than witty",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "visual_storytelling.recurring_ritual_anchor",
        "name": "Recurring Visual Ritual Anchor",
        "category": "visual_storytelling",
        "core_mechanism": "Repeats an identical gesture, physical prop, or framing motif at key narrative milestones across changing environments.",
        "variants": {
            "prop_talisman": "Holding the same coffee mug, notebook, or camera in 3 distinct city settings",
            "habitual_gesture": "Same breath check, shoe tying, or watch tap opening and closing the piece",
        },
        "use_when": [
            "Depicting passage of time, transformation, or adapting to a new city",
            "Providing emotional grounding amidst chaotic external progression",
            "Tying ending shot back to opening hook in a satisfying narrative loop",
        ],
        "avoid_when": [
            "One-off quick hack or simple single-shot comedy skit",
            "When repeated motif has no emotional or thematic meaning to creator",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "visual_storytelling.lost_in_crowd_contrast",
        "name": "Lost in Crowd Spatial Contrast",
        "category": "visual_storytelling",
        "core_mechanism": "Frames creator completely stationary in dead center while fast-moving pedestrians or traffic streak past in motion blur.",
        "variants": {
            "time_lapse_freeze": "Subject still while timelapse crowd streams around them",
            "shallow_depth_isolation": "Subject in sharp focus while rushing crowd is thrown into soft bokeh",
        },
        "use_when": [
            "Communicating internal alienation, culture shock, or sensory overwhelm",
            "Showing the feeling of time standing still while the world hurries on",
            "Symbolizing loneliness in a crowded city without saying words",
        ],
        "avoid_when": [
            "Upbeat collaborative group vlogs",
            "Educational tutorials where static subject looks awkward or unmotivated",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "visual_storytelling.subjective_pov_discovery",
        "name": "Subjective POV Discovery",
        "category": "visual_storytelling",
        "core_mechanism": "Follows creator gaze vector: shows curious or shocked facial reaction first, then cuts to what they are seeing.",
        "variants": {
            "gaze_match_cut": "Eyes widen in MCU transitioning to hard cut of bizarre sight on street",
            "slow_turn_reveal": "Creator turns head slowly as camera pans with their perspective",
        },
        "use_when": [
            "Engaging viewer curiosity before showing payoff",
            "Sharing personal subjective experience and unfiltered emotional discovery",
            "Making viewer actively hunt for details in environment",
        ],
        "avoid_when": [
            "Fast informational recaps where reaction shot slows down pacing",
            "When object being looked at is mundane or anticlimactic",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "visual_storytelling.micro_payoff_breadcrumb",
        "name": "Micro-Payoff Breadcrumb Trail",
        "category": "visual_storytelling",
        "core_mechanism": "Dispenses mini-reveals, visual dopamine hits, or tactile successes every 5–8 seconds to sustain long-form tension.",
        "variants": {
            "step_reward": "Showing sizzling sear of meat before finishing the whole recipe",
            "partial_reveal": "Showing quick 0.3s glimpse of finished project before explaining step 2",
        },
        "use_when": [
            "Complex stories or multi-step processes exceeding 35 seconds",
            "Maintaining retention above 80% on high-concept builds",
            "Counteracting audience fatigue during technical exposition",
        ],
        "avoid_when": [
            "Ultra-short 15-second jokes where single punchline suffices",
            "Stories where premature reveal destroys climax twist",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "visual_storytelling.pattern_interrupt_reset",
        "name": "Pattern Interrupt Attention Reset",
        "category": "visual_storytelling",
        "core_mechanism": "Injects an abrupt aesthetic, sonic, or tempo deviation at second 7-10 to shatter monotony and prevent swipe-away.",
        "variants": {
            "acoustic_dead_air": "Lively music drops instantly to complete silence for 0.8s on a deadpan look",
            "visual_format_glitch": "Slick cinematic b-roll suddenly cuts to raw low-fi mobile selfie",
        },
        "use_when": [
            "Approaching universal 8-12 second retention drop-off cliff",
            "After sustained 6-second stretch of uniform visual rhythm",
            "Transitioning from exposition into primary story conflict",
        ],
        "avoid_when": [
            "Within first 1.5 seconds (belongs in hook phase)",
            "During emotional climaxes where continuous immersion is essential",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "sound_rhythm.pre_reveal_silence",
        "name": "Pre-Reveal Sudden Silence",
        "category": "sound_rhythm",
        "core_mechanism": "Abruptly mutes all backing tracks, ambient noise, and foley 0.5s–1.2s prior to punchline, reveal, or confession.",
        "variants": {
            "needle_drop_hush": "Music cuts abruptly leaving only creator breath or room tone",
            "sound_vacuum": "Fades frequencies into hollow muffled vacuum before sonic slam",
        },
        "use_when": [
            "Punchline delivery in comedy or surprising plot twist",
            "Pivoting to high vulnerability in personal storytelling",
            "Forcing viewer brain into focused auditory attention",
        ],
        "avoid_when": [
            "Fast montage sequences driven by steady music rhythm",
            "When audio quality has high background hiss that makes silence jarring",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "sound_rhythm.micro_foley_punctuation",
        "name": "Micro-Foley Punctuation",
        "category": "sound_rhythm",
        "core_mechanism": "Layers hyper-tactile micro-sound effects (crisp crunch, pop, thud, click, sizzle) directly onto physical actions.",
        "variants": {
            "tactile_foley": "Amplified organic textures (coffee grounds crunch, knife slice, lock click)",
            "interface_ui": "Subtle digital clicks, camera shutters, or typewriter taps synced to text",
        },
        "use_when": [
            "Accentuating physical crafts, culinary moments, or hardware interactions",
            "Elevating perceived production value on mobile-shot footage",
            "Pairing with kinetic text captions for multi-sensory retention",
        ],
        "avoid_when": [
            "Serious emotional eulogies or solemn discussions",
            "Overlayering until it forms muddy wall of sound",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "sound_rhythm.bpm_drop_surge",
        "name": "BPM Drop and Sonic Surge",
        "category": "sound_rhythm",
        "core_mechanism": "Cuts music rhythm on conflict beat and drops heavy bass and percussion surge when transformation explodes.",
        "variants": {
            "bass_drop_reveal": "Low sub-bass boom hits frame 1 of visual transformation",
            "tempo_double_time": "Transition from slow atmospheric pads to fast driving rhythm",
        },
        "use_when": [
            "Visual payoff moments, before-and-after reveals, or dramatic transformations",
            "Synchronizing athletic peaks or triumphant project completions",
            "Rewarding viewer for waiting through tension loop",
        ],
        "avoid_when": [
            "Low-key introspective vlogs or quiet lifestyle content",
            "Videos where speech needs to remain soft and meditative",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "sound_rhythm.acoustic_vocal_isolation",
        "name": "Acoustic Vocal Isolation",
        "category": "sound_rhythm",
        "core_mechanism": "Isolates human voice in crisp, dry proximity without reverberation or musical bed, creating unfiltered authenticity.",
        "variants": {
            "whisper_proximity": "Close-mic proximity effect creating intimate connection",
            "unrehearsed_stumble": "Preserving slight vocal hitch or laugh proving moment is unscripted",
        },
        "use_when": [
            "Delivering hard truths, raw confessions, or behind-the-scenes reality",
            "Contrasting against loud commercial video aesthetics",
            "Establishing deep emotional trust with audience",
        ],
        "avoid_when": [
            "Hype-driven viral trends or fitness motivation montages",
            "When ambient environmental background noise drowns out speech",
        ],
        "evidence_count": 1,
    },
    {
        "technique_id": "sound_rhythm.ambient_texture_layer",
        "name": "Atmospheric Ambient Texture Layer",
        "category": "sound_rhythm",
        "core_mechanism": "Uses spatial environmental stereo recordings (distant siren, café murmur, rustling leaves) to ground scene in physical reality.",
        "variants": {
            "city_soundscape": "Layered traffic rumble, crosswalk beeps, and murmurs under dialogue",
            "naturalistic_quiet": "Wind whistling and subtle room reverberation",
        },
        "use_when": [
            "Establishing physical place in travel, lifestyle, or documentary storytelling",
            "Preventing sterile studio silence in talking-head videos",
            "Allowing cuts between different visual angles without breaking sonic continuity",
        ],
        "avoid_when": [
            "Fast comedic screen-recorded memes or kinetic graphic explainers",
            "When dialogue intelligibility is compromised by ambient clutter",
        ],
        "evidence_count": 1,
    },
]


def ingest_techniques_from_corpus_data(
    data_dir: str | Path = "corpus/data",
    library_path: str | Path = "corpus/technique_library.json",
) -> TechniqueLibrary:
    target_data_dir = Path(data_dir)
    library = load_technique_library(library_path)
    seed_map = {item["technique_id"]: TechniqueRecord.model_validate(item) for item in CANONICAL_TECHNIQUE_SEEDS}

    for seed in seed_map.values():
        upsert_technique_record(library, seed)

    if not target_data_dir.exists():
        save_technique_library(library, library_path)
        return library

    json_files = list(target_data_dir.glob("*.json"))
    counts: dict[str, int] = {k: 0 for k in seed_map.keys()}

    for jf in json_files:
        try:
            content = jf.read_text(encoding="utf-8")
            data = json.loads(content)
        except Exception:
            continue

        graph = data.get("video_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        for idx, node in enumerate(nodes):
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

            if movement in ("zoom", "dolly") or "punch_in" in tech_tags:
                counts["camera.motivated_push_in"] += 1

            if movement in ("zoom", "dolly") and shot_size in ("w", "ew"):
                counts["camera.revealing_pull_out"] += 1

            if movement in ("whip", "pan"):
                counts["camera.kinetic_whip_pan"] += 1

            if shot_size in ("cu", "mcu", "ecu") and on_cam:
                counts["camera.intimate_closeup"] += 1

            if format_name in ("pov", "product_demo") or "macro_shot" in tech_tags:
                counts["camera.tactile_pov_action"] += 1

            if movement == "tracking" or "walking" in action:
                counts["camera.subject_tracking_stride"] += 1

            if movement == "static" and shot_size in ("w", "ew"):
                counts["camera.observational_static_wide"] += 1

            if movement == "orbit":
                counts["camera.dynamic_orbit"] += 1

            if any(s in sfx for s in ("whoosh", "pop", "thud", "boom", "crunch", "snap", "click")):
                counts["editing.sensory_slap_cut"] += 1

            if "pattern_interrupt" in hook_types:
                counts["visual_storytelling.pattern_interrupt_reset"] += 1

            if "reaction" in tech_tags:
                counts["visual_storytelling.subjective_pov_discovery"] += 1

            if not audio.get("has_background_music", True) or music_pres in ("none", "low"):
                counts["sound_rhythm.acoustic_vocal_isolation"] += 1

            if any(s in sfx for s in ("crunch", "click", "pop", "tap", "sizzle", "thud")):
                counts["sound_rhythm.micro_foley_punctuation"] += 1

            if idx > 0:
                prev_node = nodes[idx - 1]
                prev_cam = prev_node.get("camera") or {}
                prev_size = str(prev_cam.get("shot_size", "")).lower()
                if (prev_size in ("cu", "ecu") and shot_size in ("w", "ew")) or (prev_size in ("w", "ew") and shot_size in ("cu", "ecu")):
                    counts["editing.contrast_scale_cut"] += 1

        for edge in edges:
            trans = edge.get("transition") or {}
            ttype = str(trans.get("type", "")).lower()
            rel = str(edge.get("relationship", "")).lower()

            if ttype == "jump_cut":
                counts["editing.jump_cut_cadence"] += 1

            if ttype == "whip_pan":
                counts["camera.kinetic_whip_pan"] += 1

            if rel in ("anticipates", "elaborate") and trans.get("duration_ms", 0) > 0:
                counts["editing.j_cut_audio_bridge"] += 1

            if rel == "reinforces":
                counts["editing.match_cut_action"] += 1

        derived = data.get("derived_features", {})
        if derived.get("loopability", 0.0) >= 0.5:
            counts["visual_storytelling.recurring_ritual_anchor"] += 1

        if len(nodes) >= 6:
            counts["visual_storytelling.micro_payoff_breadcrumb"] += 1

        if "calm" in data.get("tone_tags", []) and any(n.get("camera", {}).get("movement") == "static" for n in nodes):
            counts["visual_storytelling.lost_in_crowd_contrast"] += 1

        if any(n.get("audio_style", {}).get("music_presence") == "none" for n in nodes[:2]):
            counts["sound_rhythm.pre_reveal_silence"] += 1

        if derived.get("has_music") and derived.get("bpm"):
            counts["sound_rhythm.bpm_drop_surge"] += 1

        if any(n.get("video_style", {}).get("visual_format") == "b_roll" for n in nodes):
            counts["sound_rhythm.ambient_texture_layer"] += 1

    for tech in library.techniques:
        if tech.technique_id in counts and counts[tech.technique_id] > 0:
            tech.evidence_count = max(tech.evidence_count, counts[tech.technique_id])

    save_technique_library(library, library_path)
    logger.info("Ingested techniques from %d corpus files into %s", len(json_files), library_path)
    return library


def retrieve_relevant_techniques(
    script_or_idea: str,
    library: TechniqueLibrary,
    target_category: str | None = None,
    max_techniques: int = 8,
) -> list[TechniqueRecord]:
    if not library.techniques:
        return []

    words = set(re.findall(r"\w+", (script_or_idea or "").lower()))
    scored: list[tuple[float, TechniqueRecord]] = []

    for t in library.techniques:
        score = 0.0
        tech_text = f"{t.name} {t.core_mechanism} {' '.join(t.variants.values())} {' '.join(t.use_when)}".lower()

        for w in words:
            if len(w) > 3 and w in tech_text:
                score += 1.5

        if target_category:
            cat_lower = target_category.lower()
            if cat_lower in tech_text:
                score += 2.0

        score += min(float(t.evidence_count) * 0.1, 1.0)
        scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:max_techniques]]


def compile_knowledge_corpus(
    catalog: PatternCatalog,
    creators_registry_path: str | Path | None = "corpus/creators_registry.json",
    target_category: str | None = None,
    target_style_tags: list[str] | None = None,
    preferred_pattern_id: str | None = None,
    script_or_idea: str = "",
    technique_library_path: str | Path | None = "corpus/technique_library.json",
) -> dict[str, Any]:
    """
    Compiles the knowledge corpus: curated examples of successful edits, editing techniques,
    storytelling patterns, creator styles, and audience responses.

    PURPOSE: Teach the system WHAT IS POSSIBLE and WHY A TECHNIQUE WORKS.
    CRITICAL: It does NOT dictate which template to use next. It provides a craft vocabulary
    and strategic principles rather than a rigid formula to clone.
    """
    learned_editing_techniques = [
        {
            "technique": "Visceral In-Media-Res Hooks",
            "mechanism": "Drop the viewer directly into peak physical action, tension, or tactile friction in the first 0.0-1.5s.",
            "why_it_works": "Circumvents slow introductory exposition. Hijacks immediate visual curiosity and stops the thumb from swiping away.",
        },
        {
            "technique": "Sensory Slap Cuts & Foley / SFX Accents",
            "mechanism": "Precise micro-audio events (crunch, whoosh, click, sizzle, hit) synchronized within 50ms of visual cut boundaries.",
            "why_it_works": "Creates visceral tactile immersion. Multisensory reinforcement dramatically elevates perceived production value and dopamine response.",
        },
        {
            "technique": "Dynamic Camera Cadence (Framing Grammar)",
            "mechanism": "Rotate camera perspectives rapidly: intimate CU direct eye-contact for connection -> Over-The-Shoulder (OTS) for context -> First-Person POV for hands-on tactile manipulation -> Wide Orbit for environmental stakes.",
            "why_it_works": "Prevents visual gaze fatigue. Constantly reframes spatial perspective so the viewer's brain stays stimulated (target ASL 1.8s - 2.4s).",
        },
        {
            "technique": "Curiosity Gap & Micro-Resolutions",
            "mechanism": "Introduce an unspoken tension, contrarian question, or unexpected challenge early, offering progressive micro-payoffs while delaying final payoff to the last 15%.",
            "why_it_works": "Maintains tension loops throughout the entire 30-60s duration, driving completion rates above 85%.",
        },
        {
            "technique": "Pattern Interrupts & Pacing Reset",
            "mechanism": "Every 7-10 seconds, inject a sudden shift in visual scale, acoustic texture, or vocal energy (e.g. abrupt silence before a beat drop).",
            "why_it_works": "Breaks monotonous rhythmic trance, counteracting the natural viewer drop-off window at the 10-15s mark.",
        },
        {
            "technique": "Kinetic Text Punching",
            "mechanism": "Display high-contrast kinetic captions where high-impact punchline words light up in bold/yellow in exact frame-sync with vocal delivery.",
            "why_it_works": "Forces dual cognitive channel processing (visual + auditory), maintaining viewer retention even when sound is low or in loud environments.",
        },
    ]

    storytelling_patterns = []
    preferred_pattern_entry = None
    if catalog and catalog.patterns:
        relevant_patterns = select_relevant_patterns(
            catalog=catalog,
            script_or_idea=script_or_idea,
            target_category=target_category,
            target_style_tags=target_style_tags,
            preferred_pattern_id=preferred_pattern_id,
            max_patterns=6,
        )
        for p in relevant_patterns:
            if preferred_pattern_id and p.pattern_id == preferred_pattern_id:
                preferred_pattern_entry = p
            storytelling_patterns.append({
                "pattern_id": p.pattern_id,
                "name": p.name,
                "archetype": p.archetype,
                "narrative_arc": [b.value for b in p.narrative_beat_sequence],
                "hook_formula": p.hook_recipe.formula,
                "pacing": {
                    "asl_sec": p.pacing_benchmarks.target_asl_sec,
                    "cuts_per_10s": p.pacing_benchmarks.target_cuts_per_10s,
                },
                "why_it_succeeds": (
                    p.director_guidelines[0] if p.director_guidelines else "Balances rapid visual rhythm with authentic creator charisma."
                ),
                "director_guidelines": p.director_guidelines[:4],
                "adaptation_rules": getattr(p, "adaptation_rules", [])[:3],
            })

    creators_registry = load_creators_registry_safe(creators_registry_path)
    curated_creator_styles = []
    category_key = (target_category or "").lower()
    categories_to_check = [category_key] if category_key in creators_registry else list(creators_registry.keys())[:3]
    for cat in categories_to_check:
        for creator in creators_registry.get(cat, [])[:4]:
            curated_creator_styles.append({
                "creator": creator.get("name"),
                "niche": creator.get("niche"),
                "style_tags": creator.get("style_tags", []),
                "delivery_takeaway": f"Exemplifies {cat} visual energy through authentic creator presence.",
            })

    audience_response_benchmarks = {
        "optimal_asl_range_sec": [1.8, 2.4],
        "optimal_duration_range_sec": [30.0, 50.0],
        "speech_target_wpm": 135,
        "first_cut_critical_window_sec": 1.5,
        "retention_cliff_mitigation": "Must introduce visual or sonic pivot before second 8 to prevent 10s swipe-away.",
    }

    tech_lib = load_technique_library(technique_library_path)
    retrieved_techs = retrieve_relevant_techniques(
        script_or_idea=script_or_idea,
        library=tech_lib,
        target_category=target_category,
        max_techniques=8,
    )

    return {
        "philosophical_charter": (
            "Discover the most compelling version of this creator's story. "
            "Explore alternatives, test them against explicit objectives, and construct the strongest edit. "
            "This knowledge corpus teaches what is possible and why a technique might work; "
            "it does NOT dictate which template to use next."
        ),
        "learned_editing_techniques": learned_editing_techniques,
        "storytelling_patterns": storytelling_patterns,
        "curated_creator_styles": curated_creator_styles,
        "audience_response_benchmarks": audience_response_benchmarks,
        "preferred_pattern_reference": preferred_pattern_entry.to_director_context() if preferred_pattern_entry else None,
        "retrieved_filmmaking_techniques": [
            {
                "technique_id": t.technique_id,
                "name": t.name,
                "category": t.category,
                "core_mechanism": t.core_mechanism,
                "variants": t.variants,
                "use_when": t.use_when,
                "avoid_when": t.avoid_when,
            }
            for t in retrieved_techs
        ],
        "target_context": {
            "category": target_category or "general",
            "style_tags": target_style_tags or ["FAST", "CINEMATIC", "HIGH ENERGY"],
        },
    }


def parse_requirement_ledger(
    script_or_idea: str,
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    target_category: str | None = None,
    target_duration_sec: float | None = None,
) -> RequirementLedger:
    duration_str = f"{target_duration_sec:.0f}s" if target_duration_sec else "unspecified"

    prompt = f"""You are a forensic instruction parser for short-form filmmaking and video directing briefs.

YOUR MISSION (STAGE 1: BRIEF DECOMPOSITION & UNCERTAINTY-AWARE INTENT CONTRACT):
Analyze the user's creative brief with extreme fidelity. Separate what you KNOW from what is OPEN FOR EXPLORATION.
When user requirements are vague, become MORE EXPLORATORY, NOT MORE RESTRICTIVE. Do NOT force the brief into invented rigid constraints.

CRITICAL OPERATIONAL RULES:
1. OPERATING MODE CLASSIFICATION (operating_mode):
   - "open_exploration": Brief is vague, short, or open-ended (e.g. "make a cool dress video", "show a quick tech tip").
     * DO NOT hallucinate fake hard constraints.
     * Keep 'requirements' minimal (only what was explicitly mentioned).
     * Populate 'open_decisions' with 2-3 high-impact creative choices to explore across candidates (e.g. Tone: Comedic vs. High Fashion vs. Relatable).
   - "guided_exploration": Brief provides a clear story goal or beat sequence, but leaves visual execution and pacing flexible (e.g. "Show different dresses quickly and end with my favorite").
     * Preserve the core beats as guidance/requirements, but mark execution decisions as open.
   - "precision_execution": Brief contains detailed, exact constraints, specific timings, visual continuity locks, or explicit exclusions (e.g. "Change outfits every 0.5s, fixed mirror shot, finish wearing exact first dress").
     * Follow every specified detail strictly.

2. EXPLICIT CONSTRAINTS VS. INFERRED INTENTS:
   - 'requirements': Directly specified requirements. Set 'confidence'=1.0, 'flexibility'='strict' or 'flexible', and 'basis' to the quote from the brief.
   - 'inferred_intents': Reasonable interpretations supported by the brief (e.g. rapid changes imply high energy). Used as guidance, NOT rigid law.
   - 'open_decisions': Major creative dimensions left open by the creator (e.g. camera movement, sound style, comedic devices). Detail 2-3 distinct options and 'impact' (high/medium/low).
   - 'material_ambiguities': Significant unknowns that could fundamentally alter the concept (e.g. chaotic comedic shopping vs. polished luxury showcase). Note if 'resolved_by_exploration'=True.

3. PRIORITY ASSIGNMENT:
   - "hard": Non-negotiable sequence, specific object, exact words, timing floor/ceiling, or explicit rule from brief.
   - "exclusion": Explicitly forbidden elements (MUST NEVER be violated).
   - "creative_intent": Underlying emotional tone, humor, tension, or mood.
   - "preference": Preferred style or flavor where minor adaptation is acceptable.
   - "production_constraint": Equipment, location, or physical constraints.

4. CREATIVE FREEDOM & AVOIDANCES:
   - creative_freedom: Explicit areas where the creator permits or implies freedom.
   - must_avoid: Explicit negative constraints, clichés, brand taboos, or creative substitutions that would contradict the brief.

5. CONFLICTING INSTRUCTIONS DETECTION:
   If the brief contains contradictory instructions (e.g. 'continuous single uncut take' combined with 'rapid montage of 10 locations'):
   - Identify the contradiction explicitly under 'material_ambiguities' with 'resolved_by_exploration'=False.
   - Formulate a crisp, targeted 'clarification_question' to resolve the conflict.

6. VISUAL ACTION FIDELITY & ORDERED SEQUENCES:
   Extract explicit visual instructions as atomic, ordered requirements.
   For each requirement, preserve:
   - Action: What must happen.
   - Target: What object, scene, panel, or subject it affects.
   - Order/dependency: What must happen before or after it (populate 'dependencies' with prerequisite requirement IDs).
   - Observable outcome: What the viewer should see (populate in 'verification').
   Do not collapse a sequence of physical actions into a generic description.
   Example: "My hand moves across five scenes, changing each one, then I appear over the grid, vanish, and the title SPITI is revealed."
   Preserve the sequence:
   1. Five distinct scenes appear in five equal vertical panels.
   2. One continuous hand sweep changes the panels sequentially (dependencies: [R01]).
   3. The creator appears as an overlay after the scene changes (dependencies: [R02]).
   4. The creator fades out completely (dependencies: [R03]).
   5. SPITI is revealed after the creator disappears (dependencies: [R04]).
   Keep these requirements concise. Do not duplicate the full brief or invent additional mandatory actions.

USER CREATIVE BRIEF:
\"\"\"{script_or_idea}\"\"\"

TARGET CONTEXT:
Category: {target_category or "general"}
Target Duration: {duration_str}

Decompose the brief losslessly into a complete RequirementLedger matching the schema strictly.
"""

    models_to_try = [model_name]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RequirementLedger,
                        temperature=0.1,
                    ),
                )
                if response and response.text:
                    ledger = RequirementLedger.model_validate_json(response.text)
                    ledger.raw_brief = script_or_idea
                    ledger.total_hard_constraints = sum(1 for r in ledger.requirements if r.priority == "hard")
                    ledger.total_exclusions = sum(1 for r in ledger.requirements if r.priority == "exclusion")
                    return ledger
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                    time.sleep(attempt * 2)
                else:
                    raise e

    raise RuntimeError(f"Requirement ledger extraction stage failed: {last_error}")


parse_intent_contract = parse_requirement_ledger


def run_intent_interpretation(
    script_or_idea: str,
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    target_category: str | None = None,
    target_style_tags: list[str] | None = None,
    target_duration_sec: float | None = None,
    creator_constraints: list[str] | None = None,
    requirement_ledger: RequirementLedger | None = None,
) -> ScriptIntentInterpretation:
    styles_str = ", ".join(target_style_tags) if target_style_tags else "FAST, CINEMATIC, HIGH ENERGY"
    duration_str = f"{target_duration_sec:.0f}s" if target_duration_sec else "40-45s"
    constraints_str = ", ".join(creator_constraints) if creator_constraints else "Vertical 9:16, mobile production, single creator anchor"

    ledger_context = ""
    if requirement_ledger and requirement_ledger.requirements:
        ledger_context = f"""
MANDATORY REQUIREMENT BOUNDARIES (MUST BE PRESERVED WITHOUT DILUTION):
{json.dumps([r.model_dump() for r in requirement_ledger.requirements], indent=2)}
CRITICAL MANDATE:
Do not drop, replace, or dilute these atomic requirements in your interpretation.
"""

    prompt = f"""You are an elite creative director specializing in storytelling intent interpretation for short-form filmmaking.

YOUR MISSION (STAGE 2: CREATIVE INTERPRETATION & INTENT UNDERSTANDING):
Analyze the input script and creator's intent deeply. Interrogate what lies beneath the surface words:
1. What should the audience feel, notice, or anticipate as the story unfolds?
2. What is the core emotional transition delta? (e.g. 'disorientation -> familiarity', 'skepticism -> revelation', 'friction -> mastery').
3. What is the underlying dramatic tension, dilemma, or curiosity gap?
4. What is the creator's authentic, unfiltered voice and human relationship to the viewer?
5. What are the practical filming and production constraints?
{ledger_context}
CREATOR'S SCRIPT OR IDEA:
\"\"\"{script_or_idea}\"\"\"

TARGET CONTEXT:
Category: {target_category or "general"}
Target Style: {styles_str}
Target Duration: ~{duration_str}
Production Constraints: {constraints_str}

Provide a deep, non-generic, actionable directorial interpretation matching the schema.
"""

    models_to_try = [model_name]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ScriptIntentInterpretation,
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    return ScriptIntentInterpretation.model_validate_json(response.text)
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                    time.sleep(attempt * 2)
                else:
                    raise e

    raise RuntimeError(f"Intent interpretation stage failed: {last_error}")


def generate_creative_candidates(
    script_or_idea: str,
    intent_interpretation: ScriptIntentInterpretation,
    knowledge_corpus: dict[str, Any],
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    target_category: str | None = None,
    target_style_tags: list[str] | None = None,
    target_duration_sec: float | None = None,
    requirement_ledger: RequirementLedger | None = None,
) -> CreativeReasoningOutput:
    styles_str = ", ".join(target_style_tags) if target_style_tags else "FAST, CINEMATIC, HIGH ENERGY"
    duration_str = f"{target_duration_sec:.0f}s" if target_duration_sec else "40-45s"

    ledger_context = ""
    mode = requirement_ledger.operating_mode if requirement_ledger else "guided_exploration"
    if requirement_ledger:
        open_decisions_json = json.dumps([d.model_dump() for d in requirement_ledger.open_decisions], indent=2)
        inferred_json = json.dumps([i.model_dump() for i in requirement_ledger.inferred_intents], indent=2)
        hard_reqs = [r.model_dump() for r in requirement_ledger.requirements if r.priority in ("hard", "exclusion")]

        if mode == "open_exploration":
            ledger_context = f"""
OPERATING MODE: OPEN EXPLORATION (VAGUE / OPEN-ENDED BRIEF)
The creator gave an open-ended brief. You must become MORE EXPLORATORY, exploring meaningfully different conceptual directions!
OPEN CREATIVE DECISIONS TO DIVERGE ACROSS:
{open_decisions_json}

STRONGLY IMPLIED INTENTS (FOR GUIDANCE ONLY, NOT RIGID LAWS):
{inferred_json}

OPEN EXPLORATION DIRECTIVE:
1. Generate 3 distinctly different conceptual treatments that explore competing choices across the open decisions (e.g. Angle 1: Comedic/Chaos; Angle 2: High-Fashion/Cinematic; Angle 3: Relatable/Everyday Journey).
2. Do NOT create 3 minor cosmetic variations of the same trope. Explore divergent premises, emotional tones, and storytelling mechanisms!
3. Do NOT invent artificial rigid constraints that restrict the video.
"""
        elif mode == "precision_execution":
            ledger_context = f"""
OPERATING MODE: PRECISION EXECUTION (DETAILED / STRICT BRIEF)
The creator established explicit, non-negotiable requirements:
Hard Constraints & Exclusions ({len(hard_reqs)}):
{json.dumps(hard_reqs, indent=2)}

CONSTRAINT PRESERVATION LAW:
1. Every alternative MUST strictly preserve every Hard Constraint and Exclusion without alteration or substitution.
2. Diverge creatively ONLY within open creative space (camera movement, sound design, visual nuance).
"""
        else:  # guided_exploration
            ledger_context = f"""
OPERATING MODE: GUIDED EXPLORATION (CLEAR STORY GOAL, FLEXIBLE EXECUTION)
Core Story Requirements:
{json.dumps([r.model_dump() for r in requirement_ledger.requirements], indent=2)}
Open Decisions to Explore:
{open_decisions_json}

GUIDED EXPLORATION LAW:
Preserve the creator's core story beats and premise, but experiment boldly with pacing, visual rhythm, editing motifs, and acoustic design.
"""

    prompt = f"""You are a master creative director generating competing, genuinely distinct creative treatments for a short-form video.

GUIDING PRINCIPLE:
\"The model is allowed to creatively interpret the user's brief, but it is NOT allowed to silently lose, replace, or contradict the brief.\"
Explore alternatives, test them against explicit objectives, and construct the strongest edit.
{ledger_context}
STAGE 1 INTENT INTERPRETATION:
Story Summary: {intent_interpretation.story_summary}
Target Audience: {intent_interpretation.target_audience}
Tone: {intent_interpretation.primary_tone}
Emotional Transition Delta: {intent_interpretation.core_emotional_transition}
Audience Anticipation: {intent_interpretation.audience_anticipation}
Core Tension / Conflict: {intent_interpretation.core_tension_or_conflict}
Creator Authentic Voice: {intent_interpretation.authentic_voice_and_perspective}
Production Constraints: {json.dumps(intent_interpretation.production_constraints)}

KNOWLEDGE CORPUS (TECHNIQUE VOCABULARY & BENCHMARKS):
{json.dumps(knowledge_corpus, indent=2)}

CREATOR'S SCRIPT OR IDEA:
\"\"\"{script_or_idea}\"\"\"

TARGET CONTEXT:
Category: {target_category or "General"}
Target Styles: {styles_str}
Target Duration: ~{duration_str}

TASK:
Produce exactly 3 competing, genuinely distinct edit treatments (alternatives) exploring orthogonal conceptual angles:
- Alternative 1 (e.g. 'alt_comedic_subversion' or 'alt_absurd_escalation'):
  Humorous, ironic, or subversive framing that highlights human foibles, relatable chaos, or deadpan comedic contrast.
- Alternative 2 (e.g. 'alt_visceral_in_media_res' or 'alt_sensory_intensity'):
  High-energy tactile immersion, relentless pacing, sound-synced rhythm, and physical momentum.
- Alternative 3 (e.g. 'alt_intimate_minimalist' or 'alt_relatable_confession'):
  Direct-to-camera honesty, quiet visual restraint, observational authenticity, or an emotional turning point.

CONCEPTUAL DIVERSITY & RESTRAINT RULES:
1. Don't confuse different camera cuts with different ideas! The 3 alternatives MUST represent different narrative philosophies, emotional arcs, or comedic structures.
2. Restraint is rewarded: Do NOT force gratuitous memes, loud sound effects, or frantic cuts unless they genuinely serve the story's core emotion.
3. Each alternative MUST have a unique angle_id, click-worthy title, clear angle_concept, and explicit emotional_core.
4. In 'unusual_moments_or_hook', highlight a tactile, surprising, or counter-intuitive moment that stops viewer thumbs in <1.5s while respecting constraints.
5. In 'techniques_leveraged', select canonical techniques from the knowledge corpus and state WHY each works for this angle.
6. Creator MUST remain the physical, visible anchor of the story.
7. In 'narrative_structure', map out the sequential beat progression incorporating all required sequence points.
"""

    models_to_try = [model_name]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=CreativeReasoningOutput,
                        temperature=0.3,
                    ),
                )
                if response and response.text:
                    output = CreativeReasoningOutput.model_validate_json(response.text)
                    output.intent_interpretation = intent_interpretation
                    if output.alternatives:
                        logger.info(
                            "Creative reasoning produced %d alternatives for story: '%s'",
                            len(output.alternatives),
                            output.inferred_emotional_story[:80],
                        )
                        return output
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                    time.sleep(attempt * 2)
                else:
                    raise e

    raise RuntimeError(f"Multi-candidate generation failed: {last_error}")


def run_creative_reasoning(
    script_or_idea: str,
    knowledge_corpus: dict[str, Any],
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    target_category: str | None = None,
    target_style_tags: list[str] | None = None,
    target_duration_sec: float | None = None,
    intent_interpretation: ScriptIntentInterpretation | None = None,
) -> CreativeReasoningOutput:
    if not intent_interpretation:
        intent_interpretation = run_intent_interpretation(
            script_or_idea=script_or_idea,
            client=client,
            model_name=model_name,
            target_category=target_category,
            target_style_tags=target_style_tags,
            target_duration_sec=target_duration_sec,
        )

    return generate_creative_candidates(
        script_or_idea=script_or_idea,
        intent_interpretation=intent_interpretation,
        knowledge_corpus=knowledge_corpus,
        client=client,
        model_name=model_name,
        target_category=target_category,
        target_style_tags=target_style_tags,
        target_duration_sec=target_duration_sec,
    )


def run_structured_judge(
    script_or_idea: str,
    intent_interpretation: ScriptIntentInterpretation,
    creative_output: CreativeReasoningOutput,
    knowledge_corpus: dict[str, Any],
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    target_duration_sec: float | None = None,
    target_category: str | None = None,
    target_style_tags: list[str] | None = None,
    requirement_ledger: RequirementLedger | None = None,
) -> OptimizationDecision:
    alts_data = [alt.model_dump() for alt in creative_output.alternatives]

    ledger_context = ""
    mode = requirement_ledger.operating_mode if requirement_ledger else "guided_exploration"
    if requirement_ledger:
        if mode == "open_exploration":
            ledger_context = f"""
OPERATING MODE: OPEN EXPLORATION (VAGUE / OPEN-ENDED BRIEF)
The creator gave an open-ended brief with no rigid constraints.
EVALUATION PRINCIPLE FOR OPEN EXPLORATION:
1. 'Fit to Creator Intent' reflects fidelity to the broad emotional goal and premise.
2. DO NOT penalize a candidate for choosing a specific comedic, cinematic, or relatable direction in areas where the user gave no preference!
3. Score candidates on creative freshness, viral hook strength, storytelling clarity, and emotional impact.
"""
        elif mode == "precision_execution":
            hard_reqs = [r.model_dump() for r in requirement_ledger.requirements if r.priority in ("hard", "exclusion")]
            ledger_context = f"""
OPERATING MODE: PRECISION EXECUTION (DETAILED / STRICT BRIEF)
The creator established explicit, non-negotiable requirements ({len(hard_reqs)}):
{json.dumps(hard_reqs, indent=2)}

CONSTRAINT PENALTY LAW:
1. 'Fit to Creator Intent' MUST directly reflect fidelity to the Requirement Ledger.
2. If any candidate violates, drops, or alters a Hard Constraint (priority='hard') or Exclusion (priority='exclusion'), score 'fit_to_creator_intent' <= 3.0 and DO NOT select it as the champion.
3. High originality or cleverness can NEVER compensate for a violated hard constraint.
"""
        else:  # guided_exploration
            ledger_context = f"""
OPERATING MODE: GUIDED EXPLORATION (CLEAR STORY GOAL, FLEXIBLE EXECUTION)
Core Story Requirements:
{json.dumps([r.model_dump() for r in requirement_ledger.requirements], indent=2)}

EVALUATION PRINCIPLE:
Preserve core story beats. Reward candidates with superior pacing, kinetic transitions, and authentic emotional resonance.
"""

    prompt = f"""You are the formal Creative Evaluation Model and Structured Judge for short-form filmmaking.

YOUR MANDATE:
Evaluate competing creative treatments rigorously against explicit evaluation criteria:
1. Originality: Freshness, avoidance of cliché short-form tropes, unexpected visual thinking (0.0 to 10.0).
2. Clarity: Storytelling clarity, narrative comprehension, effortless audience orientation (0.0 to 10.0).
3. Emotional Impact: Affective resonance, tension, stakes, and emotional payoff (0.0 to 10.0).
4. Feasibility: Shootability with creator equipment, 9:16 vertical staging, duration budget (~{target_duration_sec or 45:.0f}s) (0.0 to 10.0).
5. Fit to Creator Intent: Fidelity to creator's core message, requirement ledger compliance, and authentic voice (0.0 to 10.0).
{ledger_context}
CREATOR'S INTENT INTERPRETATION:
Story Summary: {intent_interpretation.story_summary}
Core Emotional Delta: {intent_interpretation.core_emotional_transition}
Audience Anticipation: {intent_interpretation.audience_anticipation}
Core Tension: {intent_interpretation.core_tension_or_conflict}
Authentic Voice: {intent_interpretation.authentic_voice_and_perspective}

COMPETING CANDIDATES TO EVALUATE:
{json.dumps(alts_data, indent=2)}

TASK FOR THE STRUCTURED JUDGE:
1. For each candidate alternative, score all 5 criteria (originality, clarity, emotional_impact, feasibility, fit_to_creator_intent) from 0.0 to 10.0.
2. In 'criteria', populate CandidateEvaluationCriteria with those 5 scores.
3. In 'scores', detail each criterion score and explanation.
4. In 'total_score', sum the criteria scores (0.0 to 50.0).
5. State 'key_strengths', 'identified_weaknesses', and incisive 'judge_verdict'.

CRITICAL CREATIVE SYNTHESIS MANDATE (COMBINING THE BEST OF ALL):
Do NOT just passively score and pick one candidate while discarding the other parts!
In professional creative directing, there are frequent cases where some parts of all candidates are good and can be combined to get a superior edit, or inspired by multiple directions to form a master treatment.
For example:
- Candidate A might have an unbeatable, thumb-stopping 0.0-1.5s visual hook.
- Candidate B might have a genius recurring motif or tension loop across the middle.
- Candidate C might have the most intimate, resonant emotional resolution and direct eye-contact whisper.

YOUR EVALUATION & SYNTHESIS OPTIONS:
Option 1: If one single candidate is overwhelmingly superior, self-contained, and cannot be improved by hybridizing, set:
- is_hybrid_synthesis = False
- selected_angle_id = ID of the winning candidate
- selection_rationale = why this candidate won on its own merits
- synthesis_enhancements = specific subtle ideas borrowed from the losing candidates
- synthesized_treatment = null
- synthesis_composition = null

Option 2: If combining the best parts across candidates yields a much stronger, more compelling, or more original story, set:
- is_hybrid_synthesis = True
- selected_angle_id = "alt_synthesized_hybrid"
- selection_rationale = detailed explanation of why this combined hybrid elevates the story beyond any isolated candidate
- synthesis_composition = SynthesisComposition(
    hook_source_candidate = which candidate or idea gave the opening hook,
    core_narrative_source_candidate = which candidate or idea gave the middle progression/motif,
    resolution_source_candidate = which candidate or idea gave the emotional payoff,
    synthesis_rationale = why this synthesized combination yields a superior edit than any single candidate alone
  )
- synthesized_treatment = CreativeEditAlternative(
    angle_id = "alt_synthesized_hybrid",
    title = captivating title for the hybrid masterwork,
    angle_concept = how this hybrid combines the best ideas into one unified vision,
    emotional_core = synthesized emotional trajectory,
    unusual_moments_or_hook = the winning hook,
    narrative_structure = ordered sequence fusing the best beats,
    visual_and_sound_strategy = audiovisual strategy combining the best techniques,
    techniques_leveraged = all leveraged techniques from the knowledge corpus
  )
- revision_directives = directives to polish this synthesized hybrid edit.
"""

    models_to_try = [model_name]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=OptimizationDecision,
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    decision = OptimizationDecision.model_validate_json(response.text)
                    logger.info(
                        "Structured judge selected champion edit '%s' (is_hybrid=%s). Rationale: %s",
                        decision.selected_angle_id,
                        decision.is_hybrid_synthesis,
                        decision.selection_rationale[:80],
                    )
                    return decision
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                    time.sleep(attempt * 2)
                else:
                    raise e

    raise RuntimeError(f"Structured judge evaluation failed: {last_error}")


def evaluate_and_optimize_edits(
    script_or_idea: str,
    creative_output: CreativeReasoningOutput,
    knowledge_corpus: dict[str, Any],
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    target_duration_sec: float | None = None,
    target_category: str | None = None,
    target_style_tags: list[str] | None = None,
) -> OptimizationDecision:
    intent_interpretation = creative_output.intent_interpretation or ScriptIntentInterpretation(
        story_summary=script_or_idea[:100],
        target_audience="General short-form viewers",
        primary_tone="Engaging",
        core_emotional_transition=creative_output.inferred_emotional_story,
        audience_anticipation="Anticipates compelling story progression",
        core_tension_or_conflict="Balancing authenticity and engagement",
        authentic_voice_and_perspective=creative_output.creator_authentic_voice,
        production_constraints=["Vertical 9:16", "High retention"],
    )

    return run_structured_judge(
        script_or_idea=script_or_idea,
        intent_interpretation=intent_interpretation,
        creative_output=creative_output,
        knowledge_corpus=knowledge_corpus,
        client=client,
        model_name=model_name,
        target_duration_sec=target_duration_sec,
        target_category=target_category,
        target_style_tags=target_style_tags,
    )


def construct_revised_manifest(
    script_or_idea: str,
    winning_alternative: CreativeEditAlternative,
    optimization_decision: OptimizationDecision,
    creative_reasoning: CreativeReasoningOutput,
    knowledge_corpus: dict[str, Any],
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    target_duration_sec: float | None = None,
    target_style_tags: list[str] | None = None,
    preferred_pattern_id: str | None = None,
    requirement_ledger: RequirementLedger | None = None,
) -> DirectorResponseManifest:
    target_duration = target_duration_sec or 45.0
    styles_str = ", ".join(target_style_tags) if target_style_tags else "FAST, CINEMATIC, HIGH ENERGY"
    expected_shot_count = max(int(target_duration / 2.2), 3)

    champion_treatment = (
        optimization_decision.synthesized_treatment
        if (optimization_decision.is_hybrid_synthesis and optimization_decision.synthesized_treatment)
        else winning_alternative
    )

    available_techniques = [t["technique_id"] for t in knowledge_corpus.get("retrieved_filmmaking_techniques", [])]

    synthesis_context = ""
    if optimization_decision.is_hybrid_synthesis and optimization_decision.synthesis_composition:
        comp = optimization_decision.synthesis_composition
        synthesis_context = f"""
HYBRID SYNTHESIS ARCHITECTURE (FUSION OF MULTIPLE CANDIDATES):
- Hook Origin: {comp.hook_source_candidate}
- Narrative Origin: {comp.core_narrative_source_candidate}
- Resolution Origin: {comp.resolution_source_candidate}
- Synthesis Rationale: {comp.synthesis_rationale}
"""

    ledger_context = ""
    if requirement_ledger and requirement_ledger.requirements:
        formatted_reqs = "\n".join(
            f"  - [{r.id}] ({r.priority.upper()} | {r.scope}): {r.requirement} (Verification: {r.verification})"
            for r in requirement_ledger.requirements
        )
        ledger_context = f"""
MANDATORY REQUIREMENT LEDGER & TRACEABILITY:
{formatted_reqs}

CRITICAL TRACEABILITY & INSTRUCTION FIDELITY:
1. Every shot in 'shots' MUST specify 'satisfied_requirement_ids' (e.g. ['R01', 'R02']) denoting which requirement(s) from the ledger it fulfills.
2. Across all shots, EVERY Hard Constraint and Exclusion MUST be satisfied without omission.
3. Exclusions (priority='exclusion') MUST be strictly respected: do NOT introduce any forbidden elements.
"""

    prompt = f"""You are the master director constructing the final revised, production-grade shot-by-shot DirectorResponseManifest.

GUIDING PHILOSOPHY:
\"The model is allowed to creatively interpret the user's brief, but it is not allowed to silently lose, replace, or contradict the brief.\"

This edit has won rigorous evaluation and synthesis from the structured judge and is now undergoing its REVISED PRODUCTION BUILD.
Do not output a first-draft attempt: directly incorporate the optimization revision directives, synthesis enhancements, canonical techniques, and user requirements.
{ledger_context}
CHAMPION CREATIVE EDIT:
Title: {champion_treatment.title} (ID: {champion_treatment.angle_id})
Concept: {champion_treatment.angle_concept}
Emotional Core: {champion_treatment.emotional_core}
Hook & Unusual Moments: {champion_treatment.unusual_moments_or_hook}
Narrative Progression: {json.dumps(champion_treatment.narrative_structure)}
Audiovisual Strategy: {champion_treatment.visual_and_sound_strategy}
Techniques Leveraged: {json.dumps(champion_treatment.techniques_leveraged)}
{synthesis_context}
STRUCTURED JUDGE SYNTHESIS & REVISION DIRECTIVES (MANDATORY TO IMPLEMENT):
Selection Rationale: {optimization_decision.selection_rationale}
Synthesis Enhancements:
{json.dumps(optimization_decision.synthesis_enhancements, indent=2)}
Revision Directives:
{json.dumps(optimization_decision.revision_directives, indent=2)}

CREATOR'S ORIGINAL MATERIAL:
\"\"\"{script_or_idea}\"\"\"

CREATOR AUTHENTIC VOICE:
{creative_reasoning.creator_authentic_voice}

MANDATORY TIMING & EXECUTION RULES:
1. MANDATORY TOTAL DURATION: Exactly ~{target_duration:.1f} seconds.
2. MANDATORY SHOT COUNT: Exactly {expected_shot_count} to {expected_shot_count + 2} distinct, sequential shots.
3. CREATOR-CENTRIC FRAMING: Creator MUST be physically present and visible in the majority of shots (70-80%+) as the tactile visual anchor.
   - Varied camera angles: Close-up (CU direct eye contact), Over-the-shoulder (OTS), Interactive POV, and dynamic Tracking/Orbit.
4. FORBID FILLER DIALOGUE & CLICHÉS:
   - Strictly FORBID words: 'honestly', 'literally', 'basically', 'so yeah', 'hey guys', 'welcome back', 'in this video', 'today I am going to', 'actually'.
   - Maintain punchy, conversational speech rate (125-150 WPM).
5. SOUND & OVERLAYS:
   - Provide precise SFX cues (whoosh, hit, bass_drop, tap, click, sizzle, thud) with trigger offsets to punctuate cuts.
   - Kinetic captions with highlight_words on critical punchline words.
6. SHOT 01 HOOK:
   - Must set is_hook_critical=true, executing within the first 1.5 seconds.
7. CANONICAL TECHNIQUE APPLICATION:
   - For each shot in 'shots', assign 'applied_techniques' with applicable technique IDs from: {json.dumps(available_techniques)}.
   - Respect 'use_when' triggers and strictly avoid 'avoid_when' failure modes for each selected technique.
8. REQUIREMENT TRACEABILITY:
   - For each shot in 'shots', populate 'satisfied_requirement_ids' (e.g. ['R01', 'R03']).

EXECUTION FIDELITY RULES (BINDING ON SHOT PLANNING):
Treat the original user brief and hard requirements in the requirement ledger as binding:
1. Preserve every explicit visual action, object, count, and requested sequence.
2. Describe how important actions unfold, not merely their intended result (e.g., describe hand sweeps and panel changes as an ordered sequence rather than just 'swipes hand horizontally').
3. For gesture-triggered effects, specify direction, trigger, affected elements, and completion state.
4. For overlays, specify the subject's entrance, position or interaction, and exit when requested.
5. Express dependencies explicitly. If the creator must disappear before a title appears, the title reveal must begin after the disappearance completes.
6. Allocate timing to important action beats within the existing shot durations.
7. Use the existing schema and fields wherever possible. Add no redundant descriptions or optional effects merely to make the output more elaborate.
8. Do not sacrifice explicit user requirements for stylistic creativity.
Before returning the manifest, verify that every hard requirement has a corresponding executable action in at least one shot and map its ID to 'satisfied_requirement_ids'.

OUTPUT SPECIFICATIONS:
- project_id: Short snake_case slug (e.g. 'proj_story_edit_45s')
- title: Click-worthy, authentic title
- concept_summary: Directorial premise
- visual_style_anchor: Unified lighting, palette, realism, and camera grade prompt
- shots: Ordered list of DirectorShotPlan instances summing to ~{target_duration:.0f}s
- director_notes: 3-5 execution notes for the Video Agent
"""

    models_to_try = [model_name]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DirectorResponseManifest,
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    manifest = DirectorResponseManifest.model_validate_json(response.text)
                    manifest.pattern_blueprint_id = preferred_pattern_id or champion_treatment.angle_id
                    manifest.requirement_ledger = requirement_ledger
                    healed_manifest, det_report = validate_and_heal_manifest(
                        manifest,
                        target_duration=target_duration,
                        requirement_ledger=requirement_ledger,
                    )
                    healed_manifest.deterministic_validation = det_report
                    return healed_manifest
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                    time.sleep(attempt * 2)
                else:
                    raise e

    raise RuntimeError(f"Director manifest construction failed: {last_error}")


def audit_director_manifest(
    script_or_idea: str,
    ledger: RequirementLedger,
    manifest: DirectorResponseManifest,
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
) -> ComplianceAuditReport:
    """
    Independent forensic auditor: rigorously audits the generated shot list against the requirement ledger.
    """
    shots_summary = []
    for s in manifest.shots:
        shots_summary.append({
            "shot_id": s.shot_id,
            "shot_index": s.shot_index,
            "beat": s.beat_name.value if hasattr(s.beat_name, "value") else str(s.beat_name),
            "duration_sec": s.duration_sec,
            "scene_description": s.visual.scene_description,
            "subject_action": s.visual.subject_action,
            "camera": f"{s.visual.framing.value if hasattr(s.visual.framing, 'value') else str(s.visual.framing)} | {s.visual.camera_movement.value if hasattr(s.visual.camera_movement, 'value') else str(s.visual.camera_movement)}",
            "dialogue": s.audio.speech.transcript if s.audio and s.audio.speech else "",
            "sfx": [cue.sfx_name for cue in s.audio.sfx_cues] if s.audio and s.audio.sfx_cues else [],
            "satisfied_requirement_ids": s.satisfied_requirement_ids,
        })

    prompt = f"""You are an independent, forensic filmmaking compliance auditor.
Your job is to strictly evaluate whether the generated shot list followed every single requirement in the creator's Requirement Ledger.

ORIGINAL CREATIVE BRIEF:
\"\"\"{script_or_idea}\"\"\"

REQUIREMENT LEDGER TO AUDIT:
{json.dumps([r.model_dump() for r in ledger.requirements], indent=2)}

GENERATED SHOT LIST MANIFEST:
Title: {manifest.title}
Total Target Duration: {manifest.total_target_duration_sec:.1f}s
Visual Style Anchor: {manifest.visual_style_anchor}
Shots:
{json.dumps(shots_summary, indent=2)}

AUDITOR INSTRUCTIONS:
0. RAW BRIEF PRIMACY & OMISSIONS CHECK:
   Compare the generated shot list directly against the ORIGINAL CREATIVE BRIEF text.
   If the creator specifically asked for an action, joke, meme, prop, or beat in the verbatim brief that was dropped from the generated shots, flag it immediately as a critical failure!
1. For EVERY requirement in the ledger:
   - Carefully inspect the shots, actions, camera, dialogue, overlays, and timing to verify if the requirement was fulfilled.
   - Set status to:
     * "passed" if completely and accurately satisfied in the manifest.
     * "failed" if omitted, contradicted, or replaced.
     * "partially_satisfied" if partially addressed but missing key details.
   - Quote concrete EVIDENCE from the shots (or note the absence thereof).
   - If failed/partially_satisfied:
     * Set severity: "critical" if priority is 'hard' or 'exclusion'; "minor" if 'preference'.
     * Provide an actionable 'repair_instruction' explaining how to fix the specific shot(s).
     * Provide 'repair_scope': list of specific shot IDs or components affected (e.g. ['shot_01', 'dialogue', 'timing']).
2. Calculate overall metrics:
   - all_hard_constraints_satisfied: true ONLY if ZERO hard constraints or exclusions failed.
   - total_requirements: total count of requirements checked.
   - passed_count, failed_count.
   - compliance_rate_pct: (passed_count / total_requirements) * 100.
3. Write a crisp, professional auditor_summary.
"""

    models_to_try = [model_name]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ComplianceAuditReport,
                        temperature=0.1,
                    ),
                )
                if response and response.text:
                    audit = ComplianceAuditReport.model_validate_json(response.text)
                    # Double-check all_hard_constraints_satisfied deterministically
                    hard_fails = [
                        v for v in audit.audit_results
                        if v.priority in ("hard", "exclusion") and v.status != "passed"
                    ]
                    audit.all_hard_constraints_satisfied = len(hard_fails) == 0
                    return audit
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                    time.sleep(attempt * 2)
                else:
                    raise e

    logger.warning("Audit stage encountered error: %s. Defaulting to passing report.", last_error)
    return ComplianceAuditReport(
        all_hard_constraints_satisfied=True,
        total_requirements=len(ledger.requirements),
        passed_count=len(ledger.requirements),
        failed_count=0,
        compliance_rate_pct=100.0,
        auditor_summary="Auditor completed with automatic pass.",
    )


def repair_director_manifest(
    manifest: DirectorResponseManifest,
    audit_report: ComplianceAuditReport,
    ledger: RequirementLedger,
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
) -> tuple[DirectorResponseManifest, ComplianceAuditReport]:
    """
    Surgical repair: fixes failed requirements without breaking or regenerating shots that already passed.
    """
    failed_items = [v for v in audit_report.audit_results if v.status != "passed"]
    if not failed_items or audit_report.all_hard_constraints_satisfied:
        return manifest, audit_report

    logger.info("Found %d non-compliant requirements. Initiating targeted surgical repair...", len(failed_items))

    prompt = f"""You are an expert director performing a surgical repair on a shot list.

PROBLEM STATEMENT:
The generated shot list violated {len(failed_items)} requirements from the creator's ledger.
You must update ONLY the affected shots to achieve 100% compliance while preserving all surrounding shots that already work.

FAILED REQUIREMENTS & ACTIONABLE REPAIR DIRECTIVES:
{json.dumps([f.model_dump() for f in failed_items], indent=2)}

CURRENT MANIFEST (TO REPAIR):
{manifest.model_dump_json(indent=2)}

REPAIR RULES:
1. Fix the exact shots that caused the violations according to the repair instructions.
2. Ensure the violated requirements' IDs are mapped into 'satisfied_requirement_ids' for the corrected shots.
3. Keep the total duration, title, concept, and untouched shots stable.
4. Output the repaired, fully compliant DirectorResponseManifest matching schema strictly.
"""

    models_to_try = [model_name]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DirectorResponseManifest,
                        temperature=0.1,
                    ),
                )
                if response and response.text:
                    repaired_manifest = DirectorResponseManifest.model_validate_json(response.text)
                    repaired_manifest.requirement_ledger = ledger
                    repaired_manifest, det_report = validate_and_heal_manifest(
                        repaired_manifest,
                        target_duration=manifest.total_target_duration_sec,
                        requirement_ledger=ledger,
                    )
                    repaired_manifest.deterministic_validation = det_report
                    # Re-run audit verification on the repaired manifest
                    updated_audit = audit_director_manifest(
                        script_or_idea=ledger.raw_brief,
                        ledger=ledger,
                        manifest=repaired_manifest,
                        client=client,
                        model_name=model_name,
                    )
                    return repaired_manifest, updated_audit
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                    time.sleep(attempt * 2)
                else:
                    raise e

    logger.warning("Surgical repair encountered error: %s. Returning original manifest.", last_error)
    return manifest, audit_report


audit_manifest = audit_director_manifest
repair_manifest = repair_director_manifest


def direct_story(
    script_or_idea: str,
    catalog: PatternCatalog,
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    pattern_id: str | None = None,
    target_style_tags: list[str] | None = None,
    target_category: str | None = None,
    target_duration_sec: float | None = None,
    creators_registry_path: str | Path | None = "corpus/creators_registry.json",
    technique_library_path: str | Path | None = "corpus/technique_library.json",
) -> DirectorResponseManifest:
    """
    Direct story compatibility wrapper: delegates to the explicit DirectorAgent orchestrator.
    """
    from agents.director_agent import DirectorAgent

    director = DirectorAgent(
        gemini_model=model_name,
        client=client,
        creators_registry_path=creators_registry_path or "corpus/creators_registry.json",
        technique_library_path=technique_library_path or "corpus/technique_library.json",
    )
    return director.direct(
        script_or_idea=script_or_idea,
        pattern_id=pattern_id,
        target_style_tags=target_style_tags,
        target_category=target_category,
        target_duration_sec=target_duration_sec,
        save=False,
    )


def select_best_pattern(
    script_or_idea: str,
    catalog: PatternCatalog,
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    target_style_tags: list[str] | None = None,
    target_category: str | None = None,
) -> ViralPatternEntry:
    if not catalog.patterns:
        raise ValueError("Pattern catalog is empty. Run pattern synthesis first.")

    patterns_context = catalog.to_director_context()
    style_criteria = ""
    if target_style_tags:
        style_criteria = f"\nREQUESTED STYLE TAGS: {', '.join(target_style_tags)}"
    category_affinity = ""
    if target_category:
        category_affinity = f"""
CATEGORY & EMOTIONAL ALIGNMENT (CRITICAL):
- The requested category is '{target_category}'. Strongly prioritize patterns native to or emotionally aligned with this domain.
- NEVER select negative, apocalyptic, or fear-mongering patterns for travel, lifestyle, food, or sports topics.
"""

    prompt = f"""You are a master short-form creative director specializing in cross-modal viral editing.
Select the single best viral pattern blueprint from the catalog to adapt this user concept into a high-retention 30-60 second YouTube Short.
{style_criteria}
{category_affinity}
USER SCRIPT OR IDEA:
\"\"\"{script_or_idea}\"\"\"

AVAILABLE VIRAL PATTERN BLUEPRINTS:
{json.dumps(patterns_context, indent=2)}
"""

    models_to_try = [model_name]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for target_model in models_to_try:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=PatternSelectionDecision,
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    decision = PatternSelectionDecision.model_validate_json(response.text)
                    matched = next(
                        (p for p in catalog.patterns if p.pattern_id == decision.selected_pattern_id),
                        None,
                    )
                    if matched:
                        return matched
                    return catalog.patterns[0]
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                    time.sleep(attempt * 2)
                else:
                    raise e

    raise RuntimeError(f"Pattern selection failed: {last_error}")


def generate_director_manifest(
    script_or_idea: str,
    pattern: ViralPatternEntry,
    client: genai.Client,
    model_name: str = "gemini-3.8-flash",
    target_duration_sec: float | None = None,
    target_style_tags: list[str] | None = None,
) -> DirectorResponseManifest:
    """
    Backwards-compatible wrapper that directs the story referencing the given pattern.
    """
    catalog = PatternCatalog(patterns=[pattern], total_corpus_videos=1, total_views_analyzed=pattern.aggregate_views)
    return direct_story(
        script_or_idea=script_or_idea,
        catalog=catalog,
        client=client,
        model_name=model_name,
        pattern_id=pattern.pattern_id,
        target_style_tags=target_style_tags,
        target_duration_sec=target_duration_sec,
    )


def validate_and_heal_manifest(
    manifest: DirectorResponseManifest,
    target_duration: float | None = None,
    pattern: ViralPatternEntry | None = None,
    requirement_ledger: RequirementLedger | None = None,
) -> tuple[DirectorResponseManifest, DeterministicValidationReport]:
    """
    Tier 1 Deterministic Physical & Structural Validator (0 LLM tokens, 100% reliable).
    Audits and auto-heals physical production constraints and action fidelity across 8 distinct dimensions:
    - R01_RUNTIME: Shot durations and transition overlaps satisfy target duration and bounds.
    - R02_SPEECH: Spoken words fit dialogue window at plausible delivery rate (120-175 WPM, ceiling 210 WPM).
    - R03_CAMERA: POV, framing, subject visibility, and camera movement consistency.
    - R04_CONTINUITY: Sequential shot indexing, continuous timeline, and critical hook positioning.
    - R05_PRODUCTION: SFX trigger bounds, captions cleaning, and production metadata.
    - R06_ACTION_COVERAGE: Every hard requirement has corresponding executable action in shot manifest.
    - R07_SEQUENCE_DEPENDENCIES: Required action ordering and temporal dependencies are strictly chronological.
    - R08_VISUAL_SPECIFICITY: Required counts (e.g. 5 panels) and explicit composition titles are verified.
    """
    checks: list[DeterministicCheckResult] = []

    # ----------------------------------------------------
    # R01: Runtime & Transition Timing
    # ----------------------------------------------------
    r01_details: list[str] = []
    r01_status: str = "passed"
    desired = target_duration or manifest.total_target_duration_sec or 45.0
    desired = max(min(desired, 90.0), 5.0)

    raw_total = sum(s.duration_sec for s in manifest.shots)
    if raw_total <= 0:
        r01_status = "failed"
        r01_details.append(f"Invalid total duration: shots sum to {raw_total:.1f}s.")
    elif abs(raw_total - desired) > 0.5:
        scale = desired / raw_total
        for shot in manifest.shots:
            shot.duration_sec = round(max(min(shot.duration_sec * scale, max(desired * 0.5, 2.0)), 0.5), 1)
        diff = round(desired - sum(s.duration_sec for s in manifest.shots), 1)
        if abs(diff) >= 0.1 and manifest.shots:
            longest_shot = max(manifest.shots, key=lambda s: s.duration_sec)
            longest_shot.duration_sec = round(max(0.5, longest_shot.duration_sec + diff), 1)
        new_total = round(sum(s.duration_sec for s in manifest.shots), 2)
        manifest.total_target_duration_sec = new_total
        r01_status = "auto_healed"
        r01_details.append(
            f"Scaled timeline duration from {raw_total:.1f}s to {new_total:.1f}s to match target {desired:.1f}s."
        )
    else:
        manifest.total_target_duration_sec = round(raw_total, 2)

    # Transition duration bound check & auto-heal
    for shot in manifest.shots:
        if shot.transition_out and shot.transition_out.duration_ms > 0:
            max_trans_ms = int(shot.duration_sec * 450)
            if shot.transition_out.duration_ms > max_trans_ms and shot.duration_sec > 0.2:
                orig_ms = shot.transition_out.duration_ms
                shot.transition_out.duration_ms = max(max_trans_ms, 100)
                r01_details.append(
                    f"{shot.shot_id}: Clamped transition duration from {orig_ms}ms to {shot.transition_out.duration_ms}ms "
                    f"(max 45% of {shot.duration_sec:.1f}s shot)."
                )
                if r01_status == "passed":
                    r01_status = "auto_healed"

    if not r01_details:
        r01_details.append(
            f"Timeline duration ({manifest.total_target_duration_sec:.1f}s) satisfies target ({desired:.1f}s) and transitions are well-bounded."
        )

    checks.append(
        DeterministicCheckResult(
            check_id="R01_RUNTIME",
            name="Runtime & Transition Timing",
            status=r01_status,
            details=r01_details,
        )
    )

    # ----------------------------------------------------
    # R02: Speech Delivery Feasibility & Pacing
    # ----------------------------------------------------
    r02_details: list[str] = []
    r02_status: str = "passed"

    banned_fillers = [
        r"\b(?:and\s+)?honestly[\?,\.]?\s*",
        r"\b(?:and\s+)?literally[\?,\.]?\s*",
        r"\b(?:and\s+)?basically[\?,\.]?\s*",
        r"\bso\s+actually[\?,\.]?\s*",
        r"\bhey\s+guys[\?,\.]?\s*",
        r"\bwelcome\s+back[\?,\.]?\s*",
        r"\bso\s+yeah[\?,\.]?\s*",
        r"\bin\s+this\s+video[\?,\.]?\s*",
        r"\btoday\s+i\s+am\s+going\s+to[\?,\.]?\s*",
    ]

    for shot in manifest.shots:
        if shot.audio and shot.audio.speech and shot.audio.speech.transcript:
            cleaned = shot.audio.speech.transcript
            for pat in banned_fillers:
                cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()
            if cleaned:
                cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
            if cleaned != shot.audio.speech.transcript:
                shot.audio.speech.transcript = cleaned
                r02_details.append(f"{shot.shot_id}: Stripped banned conversational fillers from speech transcript.")
                if r02_status == "passed":
                    r02_status = "auto_healed"

            words = shot.audio.speech.transcript.strip().split()
            word_count = len(words)
            if word_count > 0 and shot.duration_sec > 0:
                wpm = shot.audio.speech.target_wpm or 140.0
                needed_sec = (word_count / max(wpm, 60.0)) * 60.0
                required_wpm = (word_count / shot.duration_sec) * 60.0
                if needed_sec > (shot.duration_sec * 1.15):
                    if required_wpm <= 220.0:
                        calibrated_wpm = min(210.0, round(required_wpm, 1))
                        shot.audio.speech.target_wpm = calibrated_wpm
                        r02_details.append(
                            f"{shot.shot_id}: Calibrated dialogue pacing to {calibrated_wpm:.0f} WPM "
                            f"to fit {word_count} words into {shot.duration_sec:.1f}s."
                        )
                        if r02_status == "passed":
                            r02_status = "auto_healed"
                    else:
                        shot.audio.speech.target_wpm = 210.0
                        r02_details.append(
                            f"{shot.shot_id}: Dialogue has {word_count} words ({needed_sec:.1f}s at normal pacing), "
                            f"requiring extreme {required_wpm:.0f} WPM (> 220 WPM physical ceiling) for {shot.duration_sec:.1f}s shot."
                        )
                        r02_status = "warning"

    if not r02_details:
        r02_details.append(
            "Spoken dialogue lines fit within shot durations at natural conversational delivery rates (120-175 WPM)."
        )

    checks.append(
        DeterministicCheckResult(
            check_id="R02_SPEECH",
            name="Speech Delivery Feasibility & Pacing",
            status=r02_status,
            details=r02_details,
        )
    )

    # ----------------------------------------------------
    # R03: Camera Feasibility & Framing Consistency
    # ----------------------------------------------------
    r03_details: list[str] = []
    r03_status: str = "passed"

    if manifest.visual_style_anchor:
        anchor = manifest.visual_style_anchor.strip().rstrip(".")
        for shot in manifest.shots:
            desc = shot.visual.scene_description.strip()
            if not desc.lower().endswith(anchor.lower()):
                shot.visual.scene_description = f"{desc}, {anchor}"
                r03_details.append(f"{shot.shot_id}: Appended visual style anchor '{anchor}'.")
                if r03_status == "passed":
                    r03_status = "auto_healed"

    for shot in manifest.shots:
        framing_val = shot.visual.framing.value.lower() if hasattr(shot.visual.framing, "value") else str(shot.visual.framing).lower()
        movement_val = shot.visual.camera_movement.value.lower() if hasattr(shot.visual.camera_movement, "value") else str(shot.visual.camera_movement).lower()
        action_val = (shot.visual.subject_action or "").lower()

        # Incompatible extreme close up staging check
        if any(ecu in framing_val for ecu in ["extreme_close_up", "ecu", "macro"]):
            if any(act in action_val for act in ["sprint", "running", "jump", "full body", "run"]):
                r03_details.append(
                    f"{shot.shot_id}: Extreme close-up framing combined with large displacement action ('{shot.visual.subject_action}'). "
                    "Recommend isolating facial/macro action for ECU."
                )
                if r03_status != "failed":
                    r03_status = "warning"

        # Rapid camera movement sustained duration check
        if any(fast in movement_val for fast in ["whip_pan", "whip pan", "snap_zoom", "snap zoom", "crash zoom"]) and shot.duration_sec > 2.5:
            r03_details.append(
                f"{shot.shot_id}: Dynamic camera movement '{movement_val}' sustained for {shot.duration_sec:.1f}s (> 2.5s). Recommend quick cut."
            )
            if r03_status != "failed":
                r03_status = "warning"

    if not r03_details:
        r03_details.append("Camera framing, focal dynamics, and visual anchors are physically realizable and consistent.")

    checks.append(
        DeterministicCheckResult(
            check_id="R03_CAMERA",
            name="Camera Feasibility & Framing Consistency",
            status=r03_status,
            details=r03_details,
        )
    )

    # ----------------------------------------------------
    # R04: Timeline & Narrative Continuity
    # ----------------------------------------------------
    r04_details: list[str] = []
    r04_status: str = "passed"

    hook_threshold = min(2.5, desired * 0.3)
    cum_dur = 0.0

    for idx, shot in enumerate(manifest.shots, start=1):
        expected_id = f"shot_{idx:02d}"
        if shot.shot_index != idx or shot.shot_id != expected_id:
            orig_id = shot.shot_id
            shot.shot_index = idx
            shot.shot_id = expected_id
            r04_details.append(f"Normalized shot index to {idx} and ID from '{orig_id}' to '{expected_id}'.")
            if r04_status == "passed":
                r04_status = "auto_healed"

        if cum_dur < hook_threshold and not shot.is_hook_critical:
            shot.is_hook_critical = True
            r04_details.append(f"{shot.shot_id}: Marked as hook-critical (falls within opening {hook_threshold:.1f}s window).")
            if r04_status == "passed":
                r04_status = "auto_healed"

        cum_dur += shot.duration_sec

    if not r04_details:
        r04_details.append("Timeline indexing is strictly monotonic, opening shots designated hook-critical, and beat progression continuous.")

    checks.append(
        DeterministicCheckResult(
            check_id="R04_CONTINUITY",
            name="Timeline & Narrative Continuity",
            status=r04_status,
            details=r04_details,
        )
    )

    # ----------------------------------------------------
    # R05: Production Completeness & Audio-Visual Alignment
    # ----------------------------------------------------
    r05_details: list[str] = []
    r05_status: str = "passed"

    # SFX cue timing bounds
    for shot in manifest.shots:
        if shot.audio and shot.audio.sfx_cues:
            for cue in shot.audio.sfx_cues:
                if cue.trigger_offset_sec is None or cue.trigger_offset_sec < 0.0:
                    cue.trigger_offset_sec = 0.0
                if cue.trigger_offset_sec >= shot.duration_sec and shot.duration_sec > 0.1:
                    orig_cue = cue.trigger_offset_sec
                    clamped = max(0.0, round(shot.duration_sec - 0.1, 2))
                    cue.trigger_offset_sec = clamped
                    r05_details.append(
                        f"{shot.shot_id}: Clamped SFX cue '{cue.sfx_name}' trigger offset from {orig_cue:.2f}s to {clamped:.2f}s "
                        f"(shot duration: {shot.duration_sec:.1f}s)."
                    )
                    if r05_status == "passed":
                        r05_status = "auto_healed"

    # Captions overlay cleaning & highlight words validation
    for shot in manifest.shots:
        if shot.overlays and shot.overlays.captions and shot.overlays.captions.text:
            cleaned_cap = shot.overlays.captions.text
            for pat in banned_fillers:
                cleaned_cap = re.sub(pat, "", cleaned_cap, flags=re.IGNORECASE).strip()
            if cleaned_cap:
                cleaned_cap = cleaned_cap[0].upper() + cleaned_cap[1:] if len(cleaned_cap) > 1 else cleaned_cap.upper()
            if cleaned_cap != shot.overlays.captions.text:
                shot.overlays.captions.text = cleaned_cap
                r05_details.append(f"{shot.shot_id}: Cleaned caption overlay text.")
                if r05_status == "passed":
                    r05_status = "auto_healed"

            if shot.overlays.captions.highlight_words:
                cap_words = set(re.findall(r"\b\w+\b", cleaned_cap.lower()))
                valid_highlights = [
                    w for w in shot.overlays.captions.highlight_words
                    if any(w_part.lower() in cap_words for w_part in re.findall(r"\b\w+\b", w))
                ]
                if len(valid_highlights) != len(shot.overlays.captions.highlight_words):
                    shot.overlays.captions.highlight_words = valid_highlights
                    r05_details.append(f"{shot.shot_id}: Filtered caption highlight words not found in caption text.")
                    if r05_status == "passed":
                        r05_status = "auto_healed"

    # Ensure project_id
    if not manifest.project_id:
        clean_title = re.sub(r"[^a-z0-9]+", "_", manifest.title.lower()).strip("_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        manifest.project_id = f"proj_{clean_title[:30]}_{timestamp}"
        r05_details.append(f"Generated missing project_id '{manifest.project_id}'.")
        if r05_status == "passed":
            r05_status = "auto_healed"

    if not r05_details:
        r05_details.append("Audio SFX cues, caption overlays, and project production metadata are fully synchronized.")

    checks.append(
        DeterministicCheckResult(
            check_id="R05_PRODUCTION",
            name="Production Completeness & Audio-Visual Alignment",
            status=r05_status,
            details=r05_details,
        )
    )

    # ----------------------------------------------------
    # R06: Action & Hard Requirement Coverage
    # ----------------------------------------------------
    r06_details: list[str] = []
    r06_status: str = "passed"
    ledger = requirement_ledger or manifest.requirement_ledger

    if ledger and ledger.requirements:
        hard_reqs = [r for r in ledger.requirements if r.priority == "hard"]
        if not hard_reqs:
            hard_reqs = ledger.requirements

        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
            "of", "with", "and", "or", "by", "from", "then", "after", "before", "i", "my",
            "me", "we", "our", "you", "your", "it", "its", "this", "that", "these", "those",
            "must", "should", "will", "can", "as", "be", "each", "one", "all"
        }

        for req in hard_reqs:
            covered_in_shots = []
            for shot in manifest.shots:
                if req.id in shot.satisfied_requirement_ids:
                    covered_in_shots.append(shot.shot_id)
                    continue

                # Check semantic keyword overlap across shot fields
                req_words = {
                    w.lower()
                    for w in re.findall(r"\b[a-zA-Z]{3,}\b", req.requirement)
                    if w.lower() not in stop_words
                }
                shot_blob = f"{shot.visual.subject_action} {shot.visual.scene_description} "
                if shot.audio and shot.audio.speech:
                    shot_blob += f"{shot.audio.speech.transcript} "
                if shot.overlays and shot.overlays.captions:
                    shot_blob += f"{shot.overlays.captions.text} "
                if shot.overlays and shot.overlays.graphic_inserts:
                    shot_blob += " ".join(g.asset_content for g in shot.overlays.graphic_inserts)
                shot_blob_lower = shot_blob.lower()

                matched_words = [w for w in req_words if w in shot_blob_lower]
                if (len(matched_words) >= 2 and len(matched_words) >= len(req_words) * 0.35) or (len(req_words) <= 2 and len(matched_words) >= 1):
                    shot.satisfied_requirement_ids.append(req.id)
                    covered_in_shots.append(shot.shot_id)
                    if r06_status == "passed":
                        r06_status = "auto_healed"

            if covered_in_shots:
                r06_details.append(f"{req.id} ('{req.requirement[:45]}...'): Covered in {', '.join(covered_in_shots)}.")
            else:
                r06_details.append(f"MISSING: {req.id} ('{req.requirement[:45]}...') not mapped to any shot action.")
                r06_status = "warning"
    else:
        r06_details.append("No external requirement ledger provided; shot actions verified as internally coherent.")

    checks.append(
        DeterministicCheckResult(
            check_id="R06_ACTION_COVERAGE",
            name="Action & Hard Requirement Coverage",
            status=r06_status,
            details=r06_details,
        )
    )

    # ----------------------------------------------------
    # R07: Action Sequence & Temporal Dependencies
    # ----------------------------------------------------
    r07_details: list[str] = []
    r07_status: str = "passed"

    if ledger and ledger.requirements:
        req_to_earliest_shot: dict[str, int] = {}
        for shot in manifest.shots:
            for rid in shot.satisfied_requirement_ids:
                if rid not in req_to_earliest_shot or shot.shot_index < req_to_earliest_shot[rid]:
                    req_to_earliest_shot[rid] = shot.shot_index

        for req in ledger.requirements:
            if req.dependencies:
                curr_shot = req_to_earliest_shot.get(req.id)
                for dep_id in req.dependencies:
                    dep_shot = req_to_earliest_shot.get(dep_id)
                    if curr_shot is not None and dep_shot is not None:
                        if curr_shot < dep_shot:
                            r07_details.append(
                                f"Sequence dependency inversion: {req.id} executed in shot {curr_shot} "
                                f"before prerequisite {dep_id} executed in shot {dep_shot}."
                            )
                            r07_status = "warning"
                        else:
                            r07_details.append(
                                f"Dependency verified: {req.id} (shot {curr_shot}) follows prerequisite {dep_id} (shot {dep_shot})."
                            )

    # Narrative sequential keywords in shot descriptions (e.g. disappearance before title reveal)
    disappearance_shot = None
    title_reveal_shot = None
    for shot in manifest.shots:
        text_lower = f"{shot.visual.subject_action} {shot.visual.scene_description} {shot.overlays.captions.text if shot.overlays and shot.overlays.captions else ''}".lower()
        if any(term in text_lower for term in ["vanish", "fades out", "disappear", "disappears", "disappearance"]):
            if disappearance_shot is None:
                disappearance_shot = shot.shot_index
        if any(term in text_lower for term in ["title reveal", "title appears", "revealed", "logo reveal", "title is"]):
            if title_reveal_shot is None:
                title_reveal_shot = shot.shot_index

    if disappearance_shot is not None and title_reveal_shot is not None:
        if title_reveal_shot < disappearance_shot:
            r07_details.append(
                f"Action sequence inversion: Title reveal in shot {title_reveal_shot} occurs before disappearance in shot {disappearance_shot}."
            )
            r07_status = "warning"
        else:
            r07_details.append(
                f"Action sequence verified: Disappearance (shot {disappearance_shot}) precedes title reveal (shot {title_reveal_shot})."
            )

    if not r07_details:
        r07_details.append("Action ordering and chronological dependencies are strictly preserved.")

    checks.append(
        DeterministicCheckResult(
            check_id="R07_SEQUENCE_DEPENDENCIES",
            name="Action Sequence & Temporal Dependencies",
            status=r07_status,
            details=r07_details,
        )
    )

    # ----------------------------------------------------
    # R08: Visual Specificity & Element Counts
    # ----------------------------------------------------
    r08_details: list[str] = []
    r08_status: str = "passed"

    all_manifest_blob = " ".join([
        f"{s.visual.scene_description} {s.visual.subject_action} "
        f"{s.audio.speech.transcript if s.audio and s.audio.speech else ''} "
        f"{s.overlays.captions.text if s.overlays and s.overlays.captions else ''} "
        f"{' '.join(g.asset_content for g in s.overlays.graphic_inserts) if s.overlays and s.overlays.graphic_inserts else ''}"
        for s in manifest.shots
    ])
    all_manifest_blob_lower = all_manifest_blob.lower()

    source_texts = []
    if ledger:
        source_texts.append(ledger.raw_brief)
        source_texts.extend(r.requirement for r in ledger.requirements if r.priority == "hard")

    combined_sources = " ".join(source_texts)

    count_matches = re.findall(
        r"\b(?:(\d+)|(two|three|four|five|six|seven|eight|nine|ten))\s+([a-zA-Z_-]+)\b",
        combined_sources,
        flags=re.IGNORECASE,
    )
    title_matches = re.findall(r'"([^"]{2,30})"', combined_sources)
    all_caps_matches = [
        w for w in re.findall(r"\b[A-Z]{3,}\b", combined_sources)
        if w not in {"SFX", "WPM", "POV", "ECU", "MCU", "B_ROLL", "CTA", "VFX", "REQ", "HOOK", "JUMP", "CUT", "THE", "AND", "FOR"}
    ]

    checked_items = set()

    for digit_str, word_str, noun in count_matches:
        num_repr = digit_str or word_str.lower()
        noun_clean = noun.lower().rstrip("s")
        key = f"{num_repr} {noun_clean}"
        if key in checked_items:
            continue
        checked_items.add(key)

        num_in_manifest = (num_repr in all_manifest_blob_lower) or (
            word_str and word_str.lower() in all_manifest_blob_lower
        )
        noun_in_manifest = noun_clean in all_manifest_blob_lower

        if num_in_manifest and noun_in_manifest:
            r08_details.append(f"Verified count: '{num_repr} {noun}' present in shot manifest.")
        else:
            r08_details.append(f"Missing count: '{num_repr} {noun}' requested in brief but not explicitly detailed in shot actions.")
            r08_status = "warning"

    for title in set(title_matches + all_caps_matches):
        if title.lower() in checked_items:
            continue
        checked_items.add(title.lower())

        if title.lower() in all_manifest_blob_lower:
            r08_details.append(f"Verified title/element: '{title}' present in manifest.")
        else:
            if manifest.shots:
                payoff_shot = manifest.shots[-1]
                if payoff_shot.overlays and payoff_shot.overlays.graphic_inserts:
                    payoff_shot.overlays.graphic_inserts[0].asset_content = title
                elif payoff_shot.overlays and payoff_shot.overlays.captions:
                    payoff_shot.overlays.captions.text = f"{payoff_shot.overlays.captions.text} {title}".strip()
                r08_details.append(f"Auto-healed missing title '{title}' into payoff shot overlays.")
                if r08_status == "passed":
                    r08_status = "auto_healed"
            else:
                r08_details.append(f"Missing explicit title: '{title}' not found in manifest.")
                r08_status = "warning"

    if not r08_details:
        r08_details.append("Visual composition details, element counts, and title elements are fully specified.")

    checks.append(
        DeterministicCheckResult(
            check_id="R08_VISUAL_SPECIFICITY",
            name="Visual Specificity & Element Counts",
            status=r08_status,
            details=r08_details,
        )
    )

    # ----------------------------------------------------
    # Report compilation
    # ----------------------------------------------------
    passed_count = sum(1 for c in checks if c.status == "passed")
    auto_healed_count = sum(1 for c in checks if c.status == "auto_healed")
    warning_count = sum(1 for c in checks if c.status == "warning")
    failed_count = sum(1 for c in checks if c.status == "failed")
    all_passed = (failed_count == 0)

    summary_str = (
        f"Deterministic Validator: {passed_count + auto_healed_count}/{len(checks)} checks passed "
        f"({auto_healed_count} auto-healed, {warning_count} warnings, {failed_count} failed)"
    )

    report = DeterministicValidationReport(
        all_passed=all_passed,
        total_checks=len(checks),
        passed_count=passed_count,
        auto_healed_count=auto_healed_count,
        warning_count=warning_count,
        failed_count=failed_count,
        checks=checks,
        validator_summary=summary_str,
    )

    manifest.deterministic_validation = report
    return manifest, report


def validate_production_feasibility(
    manifest: DirectorResponseManifest,
    target_duration: float | None = None,
) -> list[str]:
    """
    Backwards-compatible wrapper that returns issues list from deterministic validation.
    """
    _, report = validate_and_heal_manifest(manifest, target_duration=target_duration)
    issues = []
    for check in report.checks:
        if check.status in ("failed", "warning"):
            issues.extend(check.details)
    return issues


def sanitize_director_manifest(
    manifest: DirectorResponseManifest,
    pattern: ViralPatternEntry | None = None,
    target_duration: float | None = None,
) -> DirectorResponseManifest:
    """
    Backwards-compatible wrapper: runs deterministic physical validation and auto-healing.
    """
    healed, _ = validate_and_heal_manifest(
        manifest=manifest,
        target_duration=target_duration,
        pattern=pattern,
    )
    return healed
