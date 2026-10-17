from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, PrivateAttr

from corpus.schema import (
    BeatName,
    CameraMovement,
    ShotSize,
    TextOverlayType,
    TransitionType,
    VisualFormat,
    VocalDelivery,
)


class ShotVisualSpec(BaseModel):
    format: VisualFormat
    scene_description: str
    subject_action: str
    face_expression: str | None = None
    gaze_direction: str = "direct_to_camera"
    camera_movement: CameraMovement
    framing: ShotSize
    lighting: str
    color_grade: str


class SFXCue(BaseModel):
    sfx_name: str
    trigger_offset_sec: float = Field(ge=0.0, default=0.0)
    volume_db: float = -3.0


class SpeechSpec(BaseModel):
    speaker: str = "creator"
    transcript: str
    vocal_delivery: VocalDelivery | str
    target_wpm: float | None = None
    emotion_tags: list[str] = Field(default_factory=list)
    voice_id: str | None = None


class ShotAudioSpec(BaseModel):
    speech: SpeechSpec | None = None
    sfx_cues: list[SFXCue] = Field(default_factory=list)


class KineticCaptionSpec(BaseModel):
    text: str
    highlight_words: list[str] = Field(default_factory=list)
    style: TextOverlayType | str = "kinetic_captions"
    position: Literal["center", "lower_third", "upper_third"] = "center"
    animation: Literal["pop", "typewriter", "slide_up", "bounce"] = "pop"


class GraphicInsertSpec(BaseModel):
    asset_type: Literal["sticker", "emoji", "image_overlay", "chart", "arrow"]
    asset_content: str
    screen_position: list[float] = Field(default_factory=lambda: [0.5, 0.5])
    trigger_offset_sec: float = 0.0
    duration_sec: float = 1.0


class ShotOverlaySpec(BaseModel):
    captions: KineticCaptionSpec | None = None
    graphic_inserts: list[GraphicInsertSpec] = Field(default_factory=list)


class ShotTransitionSpec(BaseModel):
    transition_type: TransitionType = TransitionType.JUMP_CUT
    duration_ms: int = Field(default=0, ge=0)
    vfx_snap_zoom: bool = False
    screen_shake: bool = False


class ScriptIntentInterpretation(BaseModel):
    story_summary: str = Field(description="Crisp synopsis of the script or story concept")
    target_audience: str = Field(description="Target viewer profile and mindset")
    primary_tone: str = Field(description="Dominant emotional aesthetic and energy")
    core_emotional_transition: str = Field(description="Emotional delta, e.g., 'disorientation -> familiarity' or 'skepticism -> awe'")
    audience_anticipation: str = Field(description="What should the audience feel, notice, or anticipate throughout the narrative")
    core_tension_or_conflict: str = Field(description="Core conflict, unanswered question, or tension loop")
    authentic_voice_and_perspective: str = Field(description="Creator's authentic personality, tone, and visual relationship to viewer")
    production_constraints: list[str] = Field(default_factory=list, description="Practical filming constraints like vertical 9:16 framing, mobile gear, single creator")


class CreativeEditAlternative(BaseModel):
    angle_id: str = Field(description="Unique snake_case identifier for this edit candidate, e.g. 'alt_sensory_in_media_res'")
    title: str = Field(description="High-concept title for this edit angle")
    angle_concept: str = Field(description="What makes this creative interpretation distinctive and interesting")
    emotional_core: str = Field(description="Inferred emotional subtext and core human tension")
    unusual_moments_or_hook: str = Field(description="Surprising, tactile, or counter-intuitive moment discovered and exploited")
    narrative_structure: list[str] = Field(default_factory=list, description="Ordered sequence of narrative beats / story progression")
    visual_and_sound_strategy: str = Field(description="Specific camera movements, framing, kinetic rhythms, and sound design rationale")
    techniques_leveraged: list[str] = Field(default_factory=list, description="Editing techniques drawn from the knowledge corpus and why they work")


class CreativeReasoningOutput(BaseModel):
    intent_interpretation: ScriptIntentInterpretation | None = None
    unusual_moments_discovered: list[str] = Field(default_factory=list, description="Unusual, tactile, or unexpected moments found in the story/concept")
    inferred_emotional_story: str = Field(description="The underlying emotional journey beyond the superficial topic")
    creator_authentic_voice: str = Field(description="The creator's natural tone, perspective, and core relationship to the viewer")
    alternatives: list[CreativeEditAlternative] = Field(default_factory=list, description="2-3 competing, genuinely distinct edit interpretations")


class CandidateEvaluationCriteria(BaseModel):
    originality: float = Field(ge=0.0, le=10.0, description="Freshness and avoidance of cliché short-form tropes")
    clarity: float = Field(ge=0.0, le=10.0, description="Storytelling clarity and narrative comprehension")
    emotional_impact: float = Field(ge=0.0, le=10.0, description="Resonance, tension, and affective power")
    feasibility: float = Field(ge=0.0, le=10.0, description="Shootability with creator tools, 9:16 vertical staging, and pacing")
    fit_to_creator_intent: float = Field(ge=0.0, le=10.0, description="Fidelity to the creator's true core message and authentic voice")


class OptimizationCriterionScore(BaseModel):
    criterion: str = Field(description="Objective name (e.g. Originality, Clarity, Emotional Impact, Feasibility, Fit to Creator Intent)")
    score: float = Field(ge=0.0, le=10.0, description="Numerical score from 0.0 to 10.0")
    evaluation: str = Field(description="Critical evaluation explaining why this score was awarded")


class EditEvaluation(BaseModel):
    angle_id: str = Field(description="ID of the candidate alternative being evaluated")
    criteria: CandidateEvaluationCriteria | None = None
    scores: list[OptimizationCriterionScore] = Field(default_factory=list)
    total_score: float = Field(ge=0.0, default=0.0)
    key_strengths: list[str] = Field(default_factory=list)
    identified_weaknesses: list[str] = Field(default_factory=list)
    judge_verdict: str = Field(default="", description="Detailed qualitative judge critique across the evaluation criteria")


class SynthesisComposition(BaseModel):
    hook_source_candidate: str = Field(description="Candidate ID or title providing the opening hook mechanism")
    core_narrative_source_candidate: str = Field(description="Candidate ID or title providing the primary middle story arc / motif")
    resolution_source_candidate: str = Field(description="Candidate ID or title providing the emotional payoff / resolution")
    synthesis_rationale: str = Field(description="Why this synthesized combination yields a superior edit than any single candidate alone")


class OptimizationDecision(BaseModel):
    evaluations: list[EditEvaluation] = Field(default_factory=list, description="Evaluations of all competing edit alternatives")
    selected_angle_id: str = Field(description="The winning edit alternative chosen as the foundation, or 'alt_synthesized_hybrid' if a synthesized combination was formed")
    selection_rationale: str = Field(description="Why this edit is the strongest relative to the creator's objectives")
    is_hybrid_synthesis: bool = Field(default=False, description="True if the champion is an inspired hybrid synthesizing the best elements of multiple candidates")
    synthesis_composition: SynthesisComposition | None = Field(default=None, description="Component breakdown of where hook, narrative, and resolution were drawn from")
    synthesized_treatment: CreativeEditAlternative | None = Field(default=None, description="The newly synthesized master treatment fusing the best parts of each candidate")
    synthesis_enhancements: list[str] = Field(default_factory=list, description="Strengths borrowed from other alternatives to incorporate into the final edit")
    revision_directives: list[str] = Field(default_factory=list, description="Specific directives to revise and polish the edit before finalizing")


class RequirementPriority(str):
    HARD = "hard"
    CREATIVE_INTENT = "creative_intent"
    PREFERENCE = "preference"
    EXCLUSION = "exclusion"
    PRODUCTION_CONSTRAINT = "production_constraint"


class AtomicRequirement(BaseModel):
    id: str = Field(description="Unique atomic requirement ID, e.g. R01, R02")
    category: str = Field(
        description="Category: story_sequence, visual_continuity, dialogue_audio, editing_pacing, exclusion, character_action, framing_lighting, overall_style"
    )
    requirement: str = Field(
        description="Crisp, atomic statement of what the user specified without creative expansion"
    )
    priority: Literal["hard", "creative_intent", "preference", "exclusion", "production_constraint"] = Field(
        default="hard",
        description="hard (cannot violate), creative_intent (emotional goal), preference (desired style), exclusion (explicitly forbidden), production_constraint (shootability)",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence that this is an explicit user requirement rather than an unstated assumption",
    )
    flexibility: Literal["strict", "flexible", "exploratory"] = Field(
        default="strict",
        description="strict: non-negotiable instruction; flexible: implied direction with room to adapt; exploratory: open area for creative variation",
    )
    basis: str = Field(
        default="",
        description="Verbatim phrase or specific textual evidence in the brief grounding this requirement",
    )
    scope: str = Field(
        default="global",
        description="Scope of requirement: global, opening_shot, shot_N, midpoint, final_shot, cross_shot_continuity",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Other requirement IDs this depends on (e.g. ['R01'])",
    )
    allowed_interpretation: str = Field(
        default="",
        description="Where creative interpretation is permitted without violating the core requirement",
    )
    verification: str = Field(
        default="",
        description="Exact verification rule to check if the generated manifest satisfies this requirement",
    )


class InferredIntent(BaseModel):
    value: str = Field(description="Reasonable implied intent supported by the brief (used as guidance, not rigid law)")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence that the user intended this direction")
    basis: str = Field(description="Why this direction was inferred from the brief")


class OpenCreativeDecision(BaseModel):
    decision: str = Field(description="Creative dimension left unspecified by the user (e.g. 'Overall Tone', 'Visual Rhythm', 'Ending Beat')")
    options: list[str] = Field(default_factory=list, description="Meaningfully different creative options to explore across candidates")
    impact: Literal["high", "medium", "low"] = Field(default="medium", description="Creative impact on final piece")


class MaterialAmbiguity(BaseModel):
    ambiguity: str = Field(description="Significant unknown that could fundamentally alter the video concept")
    options: list[str] = Field(default_factory=list, description="Key distinct interpretations")
    clarification_question: str | None = Field(default=None, description="Targeted high-leverage question to ask the user if needed")
    resolved_by_exploration: bool = Field(default=True, description="True if the agent can resolve this by exploring competing angles rather than interrupting the user")


class RequirementLedger(BaseModel):
    raw_brief: str = Field(description="Original verbatim creative brief from user")
    operating_mode: Literal["open_exploration", "guided_exploration", "precision_execution"] = Field(
        default="guided_exploration",
        description="open_exploration (vague brief, wide search), guided_exploration (clear goal, flexible execution), precision_execution (strict detailed brief)",
    )
    requirements: list[AtomicRequirement] = Field(
        default_factory=list,
        description="Ordered atomic requirements extracted losslessly from the brief",
    )
    inferred_intents: list[InferredIntent] = Field(
        default_factory=list,
        description="Strongly implied intents supported by the brief, treated as guidance rather than rigid constraints",
    )
    open_decisions: list[OpenCreativeDecision] = Field(
        default_factory=list,
        description="Key creative dimensions deliberately left open for agent exploration across candidate treatments",
    )
    material_ambiguities: list[MaterialAmbiguity] = Field(
        default_factory=list,
        description="Material ambiguities that can be explored via competing angles or targeted questions",
    )
    creative_freedom: list[str] = Field(
        default_factory=list,
        description="Explicit areas where the creator permits or desires creative freedom (e.g. camera movement, lighting, comedic flair, sound design)",
    )
    must_avoid: list[str] = Field(
        default_factory=list,
        description="Explicit negative constraints, taboos, or creative tropes that would undermine or dilute the idea",
    )
    total_hard_constraints: int = Field(default=0, ge=0)
    total_exclusions: int = Field(default=0, ge=0)


IntentContract = RequirementLedger


class AuditViolation(BaseModel):
    requirement_id: str = Field(description="Requirement ID tested, e.g. R01")
    requirement: str = Field(description="Statement of the requirement")
    priority: str = Field(default="hard")
    status: Literal["passed", "failed", "partially_satisfied"] = Field(
        description="passed: satisfied; failed: contradicted or omitted; partially_satisfied: partially met"
    )
    evidence: str = Field(
        description="Evidence from shot descriptions, dialogue, camera, or timing proving compliance or violation"
    )
    severity: Literal["none", "critical", "minor"] = Field(
        default="none",
        description="critical if a hard constraint or exclusion was violated, minor if preference was adapted",
    )
    repair_instruction: str | None = Field(
        default=None,
        description="Specific actionable directive to repair the non-compliant shot(s)",
    )
    repair_scope: list[str] = Field(
        default_factory=list,
        description="Targeted shots or components to repair (e.g. ['shot_01', 'audio', 'timing'])",
    )


class ComplianceAuditReport(BaseModel):
    all_hard_constraints_satisfied: bool = Field(
        default=True,
        description="True only if every single hard constraint and exclusion is passed",
    )
    total_requirements: int = Field(default=0, ge=0)
    passed_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    compliance_rate_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    audit_results: list[AuditViolation] = Field(default_factory=list)
    auditor_summary: str = Field(
        default="",
        description="Concise summary of audit verification across all requirements",
    )


class DeterministicCheckResult(BaseModel):
    check_id: str = Field(description="Check identifier (e.g. R01_RUNTIME, R02_SPEECH, R03_CAMERA, R04_CONTINUITY, R05_PRODUCTION)")
    name: str = Field(description="Descriptive check name")
    status: Literal["passed", "auto_healed", "warning", "failed"] = Field(default="passed")
    details: list[str] = Field(default_factory=list)


class DeterministicValidationReport(BaseModel):
    all_passed: bool = True
    total_checks: int = 8
    passed_count: int = 0
    auto_healed_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    checks: list[DeterministicCheckResult] = Field(default_factory=list)
    validator_summary: str = Field(default="", description="Summary of deterministic validation checks")


class DirectorShotPlan(BaseModel):
    shot_id: str
    shot_index: int = Field(ge=1)
    beat_name: BeatName
    duration_sec: float = Field(ge=0.0)
    is_hook_critical: bool = False
    visual: ShotVisualSpec
    audio: ShotAudioSpec
    overlays: ShotOverlaySpec | None = None
    transition_out: ShotTransitionSpec
    applied_techniques: list[str] = Field(default_factory=list)
    satisfied_requirement_ids: list[str] = Field(
        default_factory=list,
        exclude=True,
        description="Traceability links to Requirement Ledger IDs fulfilled by this shot (e.g. ['R01', 'R03'])",
    )


class TechniqueRecord(BaseModel):
    technique_id: str
    name: str
    category: Literal["camera", "editing", "visual_storytelling", "sound_rhythm"]
    core_mechanism: str
    variants: dict[str, str] = Field(default_factory=dict)
    use_when: list[str] = Field(default_factory=list)
    avoid_when: list[str] = Field(default_factory=list)
    evidence_count: int = 1


class TechniqueLibrary(BaseModel):
    version: str = "1.0.0"
    techniques: list[TechniqueRecord] = Field(default_factory=list)


class DirectorResponseManifest(BaseModel):
    project_id: str
    title: str
    concept_summary: str
    pattern_blueprint_id: str | None = None
    visual_style_anchor: str = ""
    aspect_ratio: Literal["9:16", "16:9"] = "9:16"
    resolution: Literal["720p", "1080p", "4k"] = "1080p"
    fps: int = 30
    total_target_duration_sec: float = Field(ge=0.0)
    shots: list[DirectorShotPlan]
    director_notes: list[str] = Field(default_factory=list)

    # In-memory pipeline metadata (Private: omitted from Gemini API schema & exported JSON)
    _requirement_ledger: Any = PrivateAttr(default=None)
    _compliance_audit: Any = PrivateAttr(default=None)
    _deterministic_validation: Any = PrivateAttr(default=None)
    _intent_interpretation: Any = PrivateAttr(default=None)
    _creative_reasoning: Any = PrivateAttr(default=None)
    _optimization_decision: Any = PrivateAttr(default=None)
    _revision_summary: list[str] = PrivateAttr(default_factory=list)

    @property
    def deterministic_validation(self) -> DeterministicValidationReport | None:
        return self._deterministic_validation

    @deterministic_validation.setter
    def deterministic_validation(self, val: DeterministicValidationReport | None) -> None:
        self._deterministic_validation = val

    @property
    def requirement_ledger(self) -> RequirementLedger | None:
        return self._requirement_ledger

    @requirement_ledger.setter
    def requirement_ledger(self, val: RequirementLedger | None) -> None:
        self._requirement_ledger = val

    @property
    def compliance_audit(self) -> ComplianceAuditReport | None:
        return self._compliance_audit

    @compliance_audit.setter
    def compliance_audit(self, val: ComplianceAuditReport | None) -> None:
        self._compliance_audit = val

    @property
    def intent_interpretation(self) -> ScriptIntentInterpretation | None:
        return self._intent_interpretation

    @intent_interpretation.setter
    def intent_interpretation(self, val: ScriptIntentInterpretation | None) -> None:
        self._intent_interpretation = val

    @property
    def creative_reasoning(self) -> CreativeReasoningOutput | None:
        return self._creative_reasoning

    @creative_reasoning.setter
    def creative_reasoning(self, val: CreativeReasoningOutput | None) -> None:
        self._creative_reasoning = val

    @property
    def optimization_decision(self) -> OptimizationDecision | None:
        return self._optimization_decision

    @optimization_decision.setter
    def optimization_decision(self, val: OptimizationDecision | None) -> None:
        self._optimization_decision = val

    @property
    def revision_summary(self) -> list[str]:
        return self._revision_summary

    @revision_summary.setter
    def revision_summary(self, val: list[str]) -> None:
        self._revision_summary = val

