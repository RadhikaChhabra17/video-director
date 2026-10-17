from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from google import genai

from corpus.director_schema import (
    ComplianceAuditReport,
    CreativeEditAlternative,
    CreativeReasoningOutput,
    DeterministicCheckResult,
    DeterministicValidationReport,
    DirectorResponseManifest,
    IntentContract,
    OptimizationDecision,
    RequirementLedger,
    ScriptIntentInterpretation,
)
from corpus.pattern_schema import PatternCatalog
from tools.director_tools import (
    audit_director_manifest,
    compile_knowledge_corpus,
    construct_revised_manifest,
    generate_creative_candidates,
    load_pattern_catalog,
    parse_requirement_ledger,
    repair_director_manifest,
    run_intent_interpretation,
    run_structured_judge,
    save_director_manifest,
    validate_and_heal_manifest,
)
from tools.pattern_tools import get_genai_client

logger = logging.getLogger("DirectorAgent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


class DirectorAgent:
    """
    Director Agent Orchestrator:
    "Discover the most compelling version of this creator's story.
    Explore alternatives, test them against explicit objectives, and construct the strongest edit."

    Explicit 7-Stage Directing Pipeline:
    1. Intent Contract: Parse brief into atomic requirements, creative freedoms, and avoidances.
    2. Knowledge Snapshot: Compile patterns, creator archetypes, and editing techniques once.
    3. Intent Interpretation: Inquire into narrative payoff, emotional transition, and audience tension.
    4. Creative Candidates: Generate competing treatments bounded by the contract.
    5. Two-Gate Structured Judge: Gate A (fidelity/feasibility) before Gate B (creative merit).
    6. Shot Planning: Expand the champion treatment into timed, executable, traceable shots.
    7. Independent Audit & Surgical Repair: Audit against contract; repair violations without rewrites.
    """

    def __init__(
        self,
        gemini_model: str = "gemini-3.8-flash",
        catalog_path: str | Path = "corpus/pattern_catalog.json",
        creators_registry_path: str | Path = "corpus/creators_registry.json",
        technique_library_path: str | Path = "corpus/technique_library.json",
        output_dir: str | Path = "corpus/director_output",
        api_key: str | None = None,
        client: genai.Client | None = None,
    ) -> None:
        self.gemini_model = os.getenv("DIRECTOR_MODEL", gemini_model)
        self.catalog_path = Path(catalog_path)
        self.creators_registry_path = Path(creators_registry_path)
        self.technique_library_path = Path(technique_library_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key
        self.client = client or get_genai_client(api_key=api_key)

    def load_catalog(self) -> PatternCatalog:
        """Loads and returns the viral pattern catalog."""
        catalog = load_pattern_catalog(self.catalog_path)
        if not catalog.patterns:
            raise ValueError(
                f"Pattern catalog at {self.catalog_path} contains no patterns. "
                "Run pattern synthesis before directing."
            )
        return catalog

    def compile_corpus(
        self,
        target_category: str | None = None,
        target_style_tags: list[str] | None = None,
        preferred_pattern_id: str | None = None,
        script_or_idea: str = "",
        catalog: PatternCatalog | None = None,
    ) -> dict[str, Any]:
        """Compiles knowledge corpus snapshot once from patterns, creator styles, and techniques."""
        cat = catalog or self.load_catalog()
        return compile_knowledge_corpus(
            catalog=cat,
            creators_registry_path=self.creators_registry_path,
            target_category=target_category,
            target_style_tags=target_style_tags,
            preferred_pattern_id=preferred_pattern_id,
            script_or_idea=script_or_idea,
            technique_library_path=self.technique_library_path,
        )

    def create_intent_contract(
        self,
        script_or_idea: str,
        target_category: str | None = None,
        target_duration_sec: float | None = None,
    ) -> IntentContract:
        """
        Stage 1: Extracts verbatim brief into atomic requirements, priorities,
        creative freedom areas, and explicit avoidances.
        """
        return parse_requirement_ledger(
            script_or_idea=script_or_idea,
            client=self.client,
            model_name=self.gemini_model,
            target_category=target_category,
            target_duration_sec=target_duration_sec,
        )

    def interpret_intent(
        self,
        script_or_idea: str,
        contract: IntentContract | None = None,
        target_category: str | None = None,
        target_style_tags: list[str] | None = None,
        target_duration_sec: float | None = None,
        creator_constraints: list[str] | None = None,
    ) -> ScriptIntentInterpretation:
        """
        Stage 2: Interprets deep narrative premise, emotional transition,
        audience anticipation, and tension loop, grounded in the intent contract.
        """
        return run_intent_interpretation(
            script_or_idea=script_or_idea,
            client=self.client,
            model_name=self.gemini_model,
            target_category=target_category,
            target_style_tags=target_style_tags,
            target_duration_sec=target_duration_sec,
            creator_constraints=creator_constraints,
            requirement_ledger=contract,
        )

    def generate_candidates(
        self,
        script_or_idea: str,
        intent_interpretation: ScriptIntentInterpretation,
        contract: IntentContract | None = None,
        knowledge_corpus: dict[str, Any] | None = None,
        target_category: str | None = None,
        target_style_tags: list[str] | None = None,
        target_duration_sec: float | None = None,
    ) -> CreativeReasoningOutput:
        """
        Stage 3: Explores competing, distinct creative treatments within the boundaries of the contract.
        """
        corpus = knowledge_corpus or self.compile_corpus(
            target_category=target_category,
            target_style_tags=target_style_tags,
            script_or_idea=script_or_idea,
        )
        return generate_creative_candidates(
            script_or_idea=script_or_idea,
            intent_interpretation=intent_interpretation,
            knowledge_corpus=corpus,
            client=self.client,
            model_name=self.gemini_model,
            target_category=target_category,
            target_style_tags=target_style_tags,
            target_duration_sec=target_duration_sec,
            requirement_ledger=contract,
        )

    def evaluate_candidates(
        self,
        script_or_idea: str,
        intent_interpretation: ScriptIntentInterpretation,
        creative_output: CreativeReasoningOutput,
        contract: IntentContract | None = None,
        knowledge_corpus: dict[str, Any] | None = None,
        target_category: str | None = None,
        target_style_tags: list[str] | None = None,
        target_duration_sec: float | None = None,
    ) -> OptimizationDecision:
        """
        Stage 4: Structured Judge enforcing Gate A (hard constraint fidelity) before Gate B (creative merit).
        """
        corpus = knowledge_corpus or self.compile_corpus(
            target_category=target_category,
            target_style_tags=target_style_tags,
            script_or_idea=script_or_idea,
        )
        return run_structured_judge(
            script_or_idea=script_or_idea,
            intent_interpretation=intent_interpretation,
            creative_output=creative_output,
            knowledge_corpus=corpus,
            client=self.client,
            model_name=self.gemini_model,
            target_duration_sec=target_duration_sec,
            target_category=target_category,
            target_style_tags=target_style_tags,
            requirement_ledger=contract,
        )

    def plan_shots(
        self,
        script_or_idea: str,
        winning_treatment: CreativeEditAlternative,
        optimization_decision: OptimizationDecision,
        creative_output: CreativeReasoningOutput,
        contract: IntentContract | None = None,
        knowledge_corpus: dict[str, Any] | None = None,
        target_category: str | None = None,
        target_style_tags: list[str] | None = None,
        target_duration_sec: float | None = None,
        preferred_pattern_id: str | None = None,
    ) -> DirectorResponseManifest:
        """
        Stage 5: Expands the champion or synthesized treatment into timed, executable, traceable shots.
        """
        corpus = knowledge_corpus or self.compile_corpus(
            target_category=target_category,
            target_style_tags=target_style_tags,
            preferred_pattern_id=preferred_pattern_id,
            script_or_idea=script_or_idea,
        )
        return construct_revised_manifest(
            script_or_idea=script_or_idea,
            winning_alternative=winning_treatment,
            optimization_decision=optimization_decision,
            creative_reasoning=creative_output,
            knowledge_corpus=corpus,
            client=self.client,
            model_name=self.gemini_model,
            target_duration_sec=target_duration_sec,
            target_style_tags=target_style_tags,
            preferred_pattern_id=preferred_pattern_id,
            requirement_ledger=contract,
        )

    def validate_deterministic(
        self,
        manifest: DirectorResponseManifest,
        target_duration_sec: float | None = None,
        requirement_ledger: RequirementLedger | None = None,
    ) -> tuple[DirectorResponseManifest, DeterministicValidationReport]:
        """
        Stage 5b / Deterministic Validator:
        Validates physical production feasibility and action fidelity without LLM tokens.
        Checks:
        - R01: Runtime & Transition Timing
        - R02: Speech Delivery Feasibility (WPM & word count)
        - R03: Camera Feasibility & Framing Consistency
        - R04: Timeline & Narrative Continuity
        - R05: Production Completeness & Audio-Visual Alignment
        - R06: Action & Hard Requirement Coverage
        - R07: Action Sequence & Temporal Dependencies
        - R08: Visual Specificity & Element Counts
        """
        return validate_and_heal_manifest(
            manifest=manifest,
            target_duration=target_duration_sec,
            requirement_ledger=requirement_ledger or manifest.requirement_ledger,
        )

    def audit(
        self,
        manifest: DirectorResponseManifest,
        contract: IntentContract,
        script_or_idea: str = "",
    ) -> ComplianceAuditReport:
        """
        Stage 6: Independent forensic auditor tests every requirement against generated shots.
        """
        brief = script_or_idea or contract.raw_brief
        return audit_director_manifest(
            script_or_idea=brief,
            ledger=contract,
            manifest=manifest,
            client=self.client,
            model_name=self.gemini_model,
        )

    def repair(
        self,
        manifest: DirectorResponseManifest,
        audit_report: ComplianceAuditReport,
        contract: IntentContract,
    ) -> tuple[DirectorResponseManifest, ComplianceAuditReport]:
        """
        Stage 7: Targeted surgical repair for failed requirements without rewriting working shots.
        """
        return repair_director_manifest(
            manifest=manifest,
            audit_report=audit_report,
            ledger=contract,
            client=self.client,
            model_name=self.gemini_model,
        )

    def direct(
        self,
        script_or_idea: str,
        pattern_id: str | None = None,
        target_style_tags: list[str] | None = None,
        target_category: str | None = None,
        target_duration_sec: float | None = None,
        save: bool = True,
    ) -> DirectorResponseManifest:
        """
        Master Directing Orchestrator:
        Executes the constraint-preserving creative directing pipeline end-to-end.
        """
        logger.info("=" * 60)
        logger.info("STARTING DIRECTING PIPELINE: '%s...'", script_or_idea[:50].replace('\n', ' '))
        logger.info("=" * 60)

        # Stage 0: Compile single unified knowledge snapshot
        logger.info("STAGE 0: Compiling Knowledge Corpus snapshot...")
        knowledge_corpus = self.compile_corpus(
            target_category=target_category,
            target_style_tags=target_style_tags,
            preferred_pattern_id=pattern_id,
            script_or_idea=script_or_idea,
        )

        # Stage 1: Build Intent Contract & Requirement Ledger
        logger.info("STAGE 1: Parsing brief into Intent Contract & Requirement Ledger...")
        contract = self.create_intent_contract(
            script_or_idea=script_or_idea,
            target_category=target_category,
            target_duration_sec=target_duration_sec,
        )
        logger.info(
            "Contract extracted [Mode: %s]: %d requirements (%d hard, %d exclusions, %d open decisions, %d avoidances)",
            contract.operating_mode.upper(),
            len(contract.requirements),
            contract.total_hard_constraints,
            contract.total_exclusions,
            len(contract.open_decisions),
            len(contract.must_avoid),
        )

        unresolved_conflicts = [a for a in contract.material_ambiguities if not a.resolved_by_exploration]
        if unresolved_conflicts:
            for c in unresolved_conflicts:
                logger.warning(
                    "[CREATIVE CONFLICT DETECTED] %s | Question: %s",
                    c.ambiguity,
                    c.clarification_question or "Please clarify contradictory instructions.",
                )

        # Stage 2: Intent Interpretation
        logger.info("STAGE 2: Interpreting creative intent, narrative tension, and emotional delta...")
        intent_interpretation = self.interpret_intent(
            script_or_idea=script_or_idea,
            contract=contract,
            target_category=target_category,
            target_style_tags=target_style_tags,
            target_duration_sec=target_duration_sec,
        )

        # Stage 3: Creative Candidates Exploration
        logger.info("STAGE 3: Generating constraint-preserving creative candidate treatments...")
        creative_output = self.generate_candidates(
            script_or_idea=script_or_idea,
            intent_interpretation=intent_interpretation,
            contract=contract,
            knowledge_corpus=knowledge_corpus,
            target_category=target_category,
            target_style_tags=target_style_tags,
            target_duration_sec=target_duration_sec,
        )

        # Stage 4: Structured Judge Evaluation (Gate A fidelity -> Gate B creativity)
        logger.info("STAGE 4: Running Two-Gate Structured Judge on candidate treatments...")
        optimization_decision = self.evaluate_candidates(
            script_or_idea=script_or_idea,
            intent_interpretation=intent_interpretation,
            creative_output=creative_output,
            contract=contract,
            knowledge_corpus=knowledge_corpus,
            target_category=target_category,
            target_style_tags=target_style_tags,
            target_duration_sec=target_duration_sec,
        )

        # Resolve champion treatment (synthesized hybrid or standalone winner)
        if optimization_decision.is_hybrid_synthesis and optimization_decision.synthesized_treatment:
            winning_treatment = optimization_decision.synthesized_treatment
            logger.info("Judge formed synthesized hybrid champion treatment: '%s'", winning_treatment.title)
        else:
            winning_treatment = next(
                (alt for alt in creative_output.alternatives if alt.angle_id == optimization_decision.selected_angle_id),
                creative_output.alternatives[0] if creative_output.alternatives else None,
            )
            if not winning_treatment:
                raise RuntimeError("No creative edit alternatives produced.")
            logger.info("Judge selected champion treatment: '%s' (%s)", winning_treatment.title, winning_treatment.angle_id)

        # Stage 5: Shot Planning
        logger.info("STAGE 5: Constructing shot-by-shot production manifest for '%s'...", winning_treatment.title)
        manifest = self.plan_shots(
            script_or_idea=script_or_idea,
            winning_treatment=winning_treatment,
            optimization_decision=optimization_decision,
            creative_output=creative_output,
            contract=contract,
            knowledge_corpus=knowledge_corpus,
            target_category=target_category,
            target_style_tags=target_style_tags,
            target_duration_sec=target_duration_sec,
            preferred_pattern_id=pattern_id,
        )

        # Stage 5b: Deterministic Physical Validator & Auto-Healer (R01-R08)
        logger.info("STAGE 5b: Executing Deterministic Physical Validator (R01-R08)...")
        manifest, det_report = self.validate_deterministic(
            manifest=manifest,
            target_duration_sec=target_duration_sec,
            requirement_ledger=contract,
        )
        manifest.deterministic_validation = det_report
        logger.info(
            "Deterministic Validator: %d/%d passed (%d auto-healed, %d warnings, %d failed). Status: %s",
            det_report.passed_count + det_report.auto_healed_count,
            det_report.total_checks,
            det_report.auto_healed_count,
            det_report.warning_count,
            det_report.failed_count,
            "ALL PASS" if det_report.all_passed else "ATTENTION NEEDED",
        )
        for check in det_report.checks:
            logger.info("  [%s] %s: %s", check.check_id, check.name, check.status.upper())
            for detail in check.details:
                logger.info("    -> %s", detail)

        # Stage 6: Independent Forensic Audit
        logger.info("STAGE 6: Auditing generated manifest against Intent Contract...")
        audit_report = self.audit(manifest=manifest, contract=contract, script_or_idea=script_or_idea)
        logger.info(
            "Audit complete: Compliance %0.1f%% (%d passed, %d failed). Hard constraints satisfied: %s",
            audit_report.compliance_rate_pct,
            audit_report.passed_count,
            audit_report.failed_count,
            audit_report.all_hard_constraints_satisfied,
        )

        # Stage 7: Targeted Surgical Repair if violations found
        if not audit_report.all_hard_constraints_satisfied:
            logger.warning("STAGE 7: Hard constraint violations detected! Executing targeted surgical repair...")
            manifest, audit_report = self.repair(
                manifest=manifest,
                audit_report=audit_report,
                contract=contract,
            )
            # Re-run deterministic validation after surgical repair to guarantee physical feasibility
            manifest, det_report = self.validate_deterministic(
                manifest=manifest,
                target_duration_sec=target_duration_sec,
                requirement_ledger=contract,
            )
            manifest.deterministic_validation = det_report
            logger.info(
                "Post-repair Deterministic Validator: %d/%d passed (%d auto-healed, %d warnings, %d failed)",
                det_report.passed_count + det_report.auto_healed_count,
                det_report.total_checks,
                det_report.auto_healed_count,
                det_report.warning_count,
                det_report.failed_count,
            )
            logger.info(
                "Post-repair Audit: Compliance %0.1f%% (%d passed, %d failed). Hard constraints satisfied: %s",
                audit_report.compliance_rate_pct,
                audit_report.passed_count,
                audit_report.failed_count,
                audit_report.all_hard_constraints_satisfied,
            )

        # Attach internal traceability in memory (excluded from serialized JSON via PrivateAttr)
        manifest.requirement_ledger = contract
        manifest.compliance_audit = audit_report
        manifest.deterministic_validation = det_report
        manifest.intent_interpretation = intent_interpretation
        manifest.creative_reasoning = creative_output
        manifest.optimization_decision = optimization_decision

        # Save to disk if requested
        if save:
            output_file = self.output_dir / f"{manifest.project_id}.json"
            save_director_manifest(manifest, output_file)
            logger.info("Director manifest saved to: %s", output_file)

        logger.info(
            "DIRECTING COMPLETE: '%s' | %d shots | %.1fs | Status: %s",
            manifest.title,
            len(manifest.shots),
            manifest.total_target_duration_sec,
            "100% Compliant" if audit_report.all_hard_constraints_satisfied else "Repaired",
        )
        return manifest
