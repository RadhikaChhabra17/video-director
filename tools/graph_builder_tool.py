from __future__ import annotations

import logging
from typing import Literal

from corpus.schema import (
    DerivedFeatures,
    EdgeRelation,
    GraphEdge,
    GraphNode,
    Transition,
    TransitionType,
    VideoGraph,
)

logger = logging.getLogger(__name__)


def build_video_graph(
    shots: list[GraphNode],
    total_duration_sec: float | None = None,
) -> tuple[VideoGraph, DerivedFeatures]:
    if not shots:
        empty_graph = VideoGraph(nodes=[], edges=[])
        empty_features = DerivedFeatures(
            shot_count=0,
            cuts_per_10s=0.0,
            has_music=False,
            bpm=None,
            wpm=None,
            loopability=None,
        )
        return empty_graph, empty_features

    sorted_shots = sorted(shots, key=lambda s: s.timestamp_range.start_sec)
    edges: list[GraphEdge] = []

    for idx in range(len(sorted_shots) - 1):
        src = sorted_shots[idx]
        dst = sorted_shots[idx + 1]

        shot_duration = src.timestamp_range.end_sec - src.timestamp_range.start_sec

        if shot_duration < 1.5:
            pacing: Literal["fast", "medium", "slow"] = "fast"
        elif shot_duration <= 2.8:
            pacing = "medium"
        else:
            pacing = "slow"

        transition_type = _infer_transition(src, dst)
        transition = Transition(type=transition_type, duration_ms=0)
        relation = _infer_edge_relationship(src, dst)

        edge = GraphEdge(
            edge_id=f"edge_{idx + 1:02d}",
            from_event_id=src.event_id,
            to_event_id=dst.event_id,
            relationship=relation,
            transition=transition,
            pacing=pacing,
        )
        edges.append(edge)

    video_graph = VideoGraph(nodes=sorted_shots, edges=edges)

    effective_duration = (
        total_duration_sec
        if total_duration_sec and total_duration_sec > 0
        else sorted_shots[-1].timestamp_range.end_sec
    )
    effective_duration = max(effective_duration, 1.0)

    shot_count = len(sorted_shots)
    cuts_per_10s = round((shot_count / effective_duration) * 10, 2)

    has_music = any(
        s.audio_style.has_background_music
        for s in sorted_shots
        if s.audio_style is not None
    )

    wpm_values = [
        s.speaker_telemetry.wpm
        for s in sorted_shots
        if s.speaker_telemetry and s.speaker_telemetry.wpm is not None
    ]
    avg_wpm = round(sum(wpm_values) / len(wpm_values), 1) if wpm_values else None

    last_shot = sorted_shots[-1]
    first_shot = sorted_shots[0]
    is_looped = (
        "loop" in last_shot.description.lower()
        or last_shot.beat_name == "cta"
        or (last_shot.transcript and first_shot.transcript and last_shot.transcript.split()[-1].lower() == first_shot.transcript.split()[0].lower())
    )
    loopability_score = 0.85 if is_looped else 0.50

    derived_features = DerivedFeatures(
        shot_count=shot_count,
        cuts_per_10s=cuts_per_10s,
        has_music=has_music,
        bpm=None,
        wpm=avg_wpm,
        loopability=loopability_score,
    )

    return video_graph, derived_features


def _infer_transition(src: GraphNode, dst: GraphNode) -> TransitionType:
    src_cam = src.camera.movement if src.camera else None
    if src_cam == "whip":
        return TransitionType.WHIP_PAN
    if src_cam == "zoom":
        return TransitionType.ZOOM_TRANSITION

    if src.video_style and "glitch" in src.video_style.visual_effects:
        return TransitionType.GLITCH

    return TransitionType.JUMP_CUT


def _infer_edge_relationship(src: GraphNode, dst: GraphNode) -> EdgeRelation:
    src_beat = str(src.beat_name).lower()
    dst_beat = str(dst.beat_name).lower()

    if src_beat == "hook" and dst_beat in ("context", "problem", "demo"):
        return EdgeRelation.INTRODUCES
    if src_beat == "context" and dst_beat in ("problem", "demo"):
        return EdgeRelation.ILLUSTRATES
    if src_beat == "problem" and dst_beat in ("demo", "solution"):
        return EdgeRelation.ILLUSTRATES
    if src_beat in ("problem", "demo") and dst_beat == "twist":
        return EdgeRelation.CONTRASTS
    if src_beat == "twist" and dst_beat in ("proof", "payoff"):
        return EdgeRelation.PROOF
    if src_beat in ("proof", "twist", "demo") and dst_beat == "payoff":
        return EdgeRelation.RESOLVES
    if dst_beat == "cta":
        return EdgeRelation.FOLLOWS

    if src_beat == dst_beat:
        src_spk = src.speaker_telemetry.speaker_id if src.speaker_telemetry else None
        dst_spk = dst.speaker_telemetry.speaker_id if dst.speaker_telemetry else None
        if src_spk and dst_spk and src_spk != dst_spk:
            if src_beat in ("demo", "twist", "hook"):
                return EdgeRelation.REINFORCES
            return EdgeRelation.ELABORATE

        if src_beat in ("context", "problem", "demo"):
            return EdgeRelation.ELABORATE
        return EdgeRelation.REINFORCES

    src_text = (src.transcript or "").strip()
    if src_text.endswith("?") or (src.ocr_text and src.ocr_text.strip().endswith("?")):
        return EdgeRelation.ILLUSTRATES

    return EdgeRelation.CUTS_TO
