export interface SFXCue {
  sfx_name: string;
  trigger_offset_sec?: number;
  volume_db?: number;
}

export interface SpeechSpec {
  speaker?: string;
  transcript: string;
  vocal_delivery?: string;
  target_wpm?: number;
  emotion_tags?: string[];
  voice_id?: string | null;
}

export interface ShotAudioSpec {
  speech?: SpeechSpec;
  sfx_cues?: SFXCue[];
}

export interface ShotVisualSpec {
  format?: string;
  scene_description: string;
  subject_action?: string;
  face_expression?: string | null;
  gaze_direction?: string | null;
  camera_movement?: string;
  framing?: string;
  lighting?: string;
  color_grade?: string;
}

export interface DirectorShotPlan {
  shot_id: string;
  shot_index: number;
  beat_name: string;
  duration_sec: number;
  is_hook_critical: boolean;
  visual: ShotVisualSpec;
  audio: ShotAudioSpec;
  overlays?: any;
  transition_out?: any;
  applied_techniques?: string[];
  satisfied_requirement_ids?: string[];
}

export interface AtomicRequirement {
  id: string;
  category: string;
  requirement: string;
  priority: 'hard' | 'creative_intent' | 'preference' | 'exclusion' | 'production_constraint';
  confidence?: number;
  flexibility?: 'strict' | 'flexible' | 'exploratory';
  basis?: string;
  scope: string;
  dependencies?: string[];
  allowed_interpretation?: string;
  verification?: string;
}

export interface InferredIntent {
  value: string;
  confidence?: number;
  basis?: string;
}

export interface OpenCreativeDecision {
  decision: string;
  options: string[];
  impact: 'high' | 'medium' | 'low';
}

export interface MaterialAmbiguity {
  ambiguity: string;
  options: string[];
  clarification_question?: string | null;
  resolved_by_exploration?: boolean;
}

export interface RequirementLedger {
  raw_brief: string;
  operating_mode?: 'open_exploration' | 'guided_exploration' | 'precision_execution';
  requirements: AtomicRequirement[];
  inferred_intents?: InferredIntent[];
  open_decisions?: OpenCreativeDecision[];
  material_ambiguities?: MaterialAmbiguity[];
  creative_freedom?: string[];
  must_avoid?: string[];
  total_hard_constraints?: number;
  total_exclusions?: number;
}

export type IntentContract = RequirementLedger;

export interface AuditViolation {
  requirement_id: string;
  requirement: string;
  priority?: string;
  status: 'passed' | 'failed' | 'partially_satisfied';
  evidence: string;
  severity: 'none' | 'critical' | 'minor';
  repair_instruction?: string | null;
  repair_scope?: string[];
}

export interface ComplianceAuditReport {
  all_hard_constraints_satisfied: boolean;
  total_requirements: number;
  passed_count: number;
  failed_count: number;
  compliance_rate_pct: number;
  audit_results?: AuditViolation[];
  auditor_summary?: string;
}

export interface DeterministicCheckResult {
  check_id: string;
  name: string;
  status: 'passed' | 'auto_healed' | 'warning' | 'failed';
  details: string[];
}

export interface DeterministicValidationReport {
  all_passed: boolean;
  total_checks: number;
  passed_count: number;
  auto_healed_count: number;
  warning_count: number;
  failed_count: number;
  checks: DeterministicCheckResult[];
  validator_summary: string;
}


export interface TechniqueRecord {
  technique_id: string;
  name: string;
  category: 'camera' | 'editing' | 'visual_storytelling' | 'sound_rhythm';
  core_mechanism: string;
  variants?: Record<string, string>;
  use_when: string[];
  avoid_when: string[];
  evidence_count?: number;
}

export interface TechniqueLibrary {
  version: string;
  techniques: TechniqueRecord[];
}

export interface ScriptIntentInterpretation {
  story_summary: string;
  target_audience: string;
  primary_tone: string;
  core_emotional_transition: string;
  audience_anticipation: string;
  core_tension_or_conflict: string;
  authentic_voice_and_perspective: string;
  production_constraints?: string[];
}

export interface CandidateEvaluationCriteria {
  originality: number;
  clarity: number;
  emotional_impact: number;
  feasibility: number;
  fit_to_creator_intent: number;
}

export interface OptimizationCriterionScore {
  criterion: string;
  score: number;
  evaluation: string;
}

export interface EditEvaluation {
  angle_id: string;
  criteria?: CandidateEvaluationCriteria;
  scores?: OptimizationCriterionScore[];
  total_score?: number;
  key_strengths?: string[];
  identified_weaknesses?: string[];
  judge_verdict?: string;
}

export interface SynthesisComposition {
  hook_source_candidate: string;
  core_narrative_source_candidate: string;
  resolution_source_candidate: string;
  synthesis_rationale: string;
}

export interface CreativeEditAlternative {
  angle_id: string;
  title: string;
  angle_concept: string;
  emotional_core: string;
  unusual_moments_or_hook: string;
  narrative_structure?: string[];
  visual_and_sound_strategy: string;
  techniques_leveraged?: string[];
}

export interface CreativeReasoningOutput {
  intent_interpretation?: ScriptIntentInterpretation;
  unusual_moments_discovered?: string[];
  inferred_emotional_story?: string;
  creator_authentic_voice?: string;
  alternatives?: CreativeEditAlternative[];
}

export interface OptimizationDecision {
  evaluations?: EditEvaluation[];
  selected_angle_id: string;
  selection_rationale: string;
  is_hybrid_synthesis?: boolean;
  synthesis_composition?: SynthesisComposition;
  synthesized_treatment?: CreativeEditAlternative;
  synthesis_enhancements?: string[];
  revision_directives?: string[];
}

export interface DirectorResponseManifest {
  project_id: string;
  title: string;
  concept_summary: string;
  pattern_blueprint_id: string;
  visual_style_anchor: string;
  aspect_ratio: string;
  resolution: string;
  fps: number;
  total_target_duration_sec: number;
  shots: DirectorShotPlan[];
  director_notes?: string[];
  requirement_ledger?: RequirementLedger;
  compliance_audit?: ComplianceAuditReport;
  deterministic_validation?: DeterministicValidationReport;
  intent_interpretation?: ScriptIntentInterpretation;
  creative_reasoning?: CreativeReasoningOutput;
  optimization_decision?: OptimizationDecision;
  revision_summary?: string[];
}

export interface ManifestSummary {
  filename: string;
  project_id: string;
  title: string;
  total_target_duration_sec: number;
  shots_count: number;
  aspect_ratio: string;
}

export interface DirectRequest {
  script: string;
  creative_pitch?: string;
  duration?: number;
  category?: string;
  style_tags?: string[];
  reference_video_id?: string;
  pattern_id?: string;
  active_direction_tag?: string;
  session_id?: string;
}

export interface StyleTransferContract {
  reference_video_id: string;
  reference_title: string;
  pattern_id?: string | null;
  pattern_name?: string | null;
  is_catalog_pattern: boolean;
  must_preserve_invariants: string[];
  target_closely_styles: string[];
  adapt_freely_content: string[];
  must_avoid: string[];
  editing_rhythm: {
    cuts_per_10s: number;
    total_shots: number;
    total_duration_sec: number;
    pacing_curve_description: string;
    has_pacing_acceleration: boolean;
  };
  visual_grammar: {
    dominant_format: string;
    dominant_framing: string;
    dominant_movement: string;
    visual_format_distribution: Record<string, number>;
  };
  audio_delivery: {
    is_measured: boolean;
    wpm?: number | null;
    vocal_delivery?: string | null;
    music_presence: string;
    music_mood?: string | null;
    sfx_cues: string[];
    audio_notes: string;
  };
  narrative_beats: Array<{
    beat_name: string;
    duration_sec: number;
    purpose: string;
    shot_count: number;
    asl_sec: number;
  }>;
  creative_modifier?: string | null;
  modifier_directives: string[];
}


export interface RefineShotRequest {
  shot?: DirectorShotPlan;
  shot_index?: number;
  manifest?: DirectorResponseManifest;
  instruction: string;
  manifest_context?: {
    title: string;
    visual_style_anchor?: string;
  };
  model?: string;
}


