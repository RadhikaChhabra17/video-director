from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from corpus.schema import (
    BeatName,
    CameraMovement,
    CreatorSetup,
    HookType,
    ShotSize,
    ToneTag,
    VocalDelivery,
)


class HookRecipe(BaseModel):
    formula: str
    hook_types: list[HookType] = Field(default_factory=list)
    first_3s_action: str
    ocr_caption_style: str


class AudiovisualRecipe(BaseModel):
    camera_movement: list[CameraMovement] = Field(default_factory=list)
    framing: list[ShotSize] = Field(default_factory=list)
    lighting_and_grade: str
    vocal_delivery: list[VocalDelivery | str] = Field(default_factory=list)
    target_wpm: float
    music_and_sfx: str


class PacingBenchmark(BaseModel):
    target_cuts_per_10s: float = Field(ge=0.0)
    target_asl_sec: float = Field(ge=0.0)
    optimal_duration_range_sec: list[float] = Field(default_factory=list)


class ViralPatternEntry(BaseModel):
    pattern_id: str
    name: str
    archetype: str
    creator_setup: CreatorSetup
    primary_category: str | None = None
    source_categories: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    tone_tags: list[ToneTag] = Field(default_factory=list)
    best_use_cases: list[str] = Field(default_factory=list)
    frequency: int = Field(default=1, ge=1)
    source_video_ids: list[str] = Field(default_factory=list)
    aggregate_views: int = Field(default=0, ge=0)
    avg_engagement_rate: float = Field(default=0.0, ge=0.0)
    hook_recipe: HookRecipe
    narrative_beat_sequence: list[BeatName] = Field(default_factory=list)
    audiovisual_recipe: AudiovisualRecipe
    pacing_benchmarks: PacingBenchmark
    director_guidelines: list[str] = Field(default_factory=list)
    adaptation_rules: list[str] = Field(default_factory=list)

    def to_director_context(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "archetype": self.archetype,
            "primary_category": self.primary_category,
            "source_categories": self.source_categories,
            "style_tags": self.style_tags,
            "creator_setup": self.creator_setup.value,
            "tone_tags": [t.value for t in self.tone_tags],
            "best_use_cases": self.best_use_cases,
            "proven_performance": {
                "aggregate_views": self.aggregate_views,
                "avg_engagement_rate": self.avg_engagement_rate,
                "sample_frequency": self.frequency,
            },
            "hook_recipe": {
                "formula": self.hook_recipe.formula,
                "hook_types": [h.value for h in self.hook_recipe.hook_types],
                "first_3s_action": self.hook_recipe.first_3s_action,
                "caption_style": self.hook_recipe.ocr_caption_style,
            },
            "narrative_arc": [b.value for b in self.narrative_beat_sequence],
            "audiovisual_direction": {
                "framing": [f.value for f in self.audiovisual_recipe.framing],
                "camera_movement": [c.value for c in self.audiovisual_recipe.camera_movement],
                "lighting_and_grade": self.audiovisual_recipe.lighting_and_grade,
                "vocal_delivery": [
                    v.value if hasattr(v, "value") else str(v)
                    for v in self.audiovisual_recipe.vocal_delivery
                ],
                "target_wpm": self.audiovisual_recipe.target_wpm,
                "music_and_sfx": self.audiovisual_recipe.music_and_sfx,
            },
            "pacing": {
                "target_cuts_per_10s": self.pacing_benchmarks.target_cuts_per_10s,
                "target_asl_sec": self.pacing_benchmarks.target_asl_sec,
                "optimal_duration_range_sec": self.pacing_benchmarks.optimal_duration_range_sec,
            },
            "director_guidelines": self.director_guidelines,
            "adaptation_rules": self.adaptation_rules,
        }


class PatternCatalog(BaseModel):
    updated_at: datetime
    total_corpus_videos: int = Field(default=0, ge=0)
    total_views_analyzed: int = Field(default=0, ge=0)
    patterns: list[ViralPatternEntry] = Field(default_factory=list)

    def to_director_context(self) -> list[dict[str, Any]]:
        return [p.to_director_context() for p in self.patterns]


def create_empty_catalog() -> PatternCatalog:
    """Explicit factory to create a pristine empty PatternCatalog."""
    from datetime import timezone
    return PatternCatalog(
        updated_at=datetime.now(timezone.utc),
        total_corpus_videos=0,
        total_views_analyzed=0,
        patterns=[],
    )

