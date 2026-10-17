import React, { useState } from 'react';
import {
  ScriptIntentInterpretation,
  CreativeReasoningOutput,
  OptimizationDecision,
} from '../types/director';
import {
  Brain,
  Compass,
  GitMerge,
  Award,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Target,
  Flame,
  ShieldAlert,
} from 'lucide-react';

interface DirectorIntelligencePanelProps {
  intent?: ScriptIntentInterpretation;
  creativeReasoning?: CreativeReasoningOutput;
  decision?: OptimizationDecision;
}

export const DirectorIntelligencePanel: React.FC<DirectorIntelligencePanelProps> = ({
  intent,
  creativeReasoning,
  decision,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'intent' | 'candidates' | 'judge'>('overview');
  const [expandedCandidate, setExpandedCandidate] = useState<string | null>(null);

  const alternatives = creativeReasoning?.alternatives || [];
  const evaluations = decision?.evaluations || [];
  const selectedAngleId = decision?.selected_angle_id;
  const isHybrid = decision?.is_hybrid_synthesis;
  const synthesis = decision?.synthesis_composition;

  if (!intent && !creativeReasoning && !decision) {
    return (
      <div className="bg-[#0b0e17]/80 glass-hud border border-white/10 rounded-2xl p-6 text-center shadow-xl">
        <Brain className="w-8 h-8 text-cyan-400 mx-auto mb-2 opacity-80" />
        <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-white">Filmmaking Intelligence Engine</h4>
        <p className="text-xs text-zinc-400 mt-1 max-w-sm mx-auto">
          Generate a cut with the AI Director to reveal the multi-candidate creative directions, intent understanding, and structured judge evaluation.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-[#0b0e17]/90 glass-hud border border-white/10 rounded-2xl p-5 shadow-xl flex flex-col gap-5">
      {/* Top Header Bar & Tabs */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="w-6 h-6 rounded-lg bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 flex items-center justify-center font-bold shrink-0">
              <Brain className="w-3.5 h-3.5" />
            </span>
            <span className="text-xs uppercase font-mono tracking-wider font-bold text-white">
              Creative Intelligence & Candidate Judge
            </span>
            {isHybrid && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30 font-semibold flex items-center gap-1">
                <GitMerge className="w-3 h-3 text-purple-400" />
                Hybrid Synthesis Active
              </span>
            )}
          </div>
          <p className="text-[11px] text-zinc-400 mt-0.5">
            Full 5-stage director chain: Intent Ingestion ➔ 3 Distinct Candidates ➔ 5-Criterion Evaluation ➔ Cross-Pollination Synthesis.
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center gap-1 bg-black/60 p-1 rounded-xl border border-white/10 text-xs font-mono overflow-x-auto max-w-full pb-1 sm:pb-1">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1 rounded-lg transition-all ${
              activeTab === 'overview'
                ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-bold shadow-sm'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('intent')}
            className={`px-3 py-1 rounded-lg transition-all ${
              activeTab === 'intent'
                ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-bold shadow-sm'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Stage 1: Intent
          </button>
          <button
            onClick={() => setActiveTab('candidates')}
            className={`px-3 py-1 rounded-lg transition-all flex items-center gap-1 ${
              activeTab === 'candidates'
                ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-bold shadow-sm'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Stage 2: Candidates ({alternatives.length})
          </button>
          <button
            onClick={() => setActiveTab('judge')}
            className={`px-3 py-1 rounded-lg transition-all flex items-center gap-1 ${
              activeTab === 'judge'
                ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-bold shadow-sm'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Stage 3: Judge & Synthesis
          </button>
        </div>
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="flex flex-col gap-4">
          {/* Champion Synthesis Banner */}
          {isHybrid && synthesis && (
            <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/40 via-cyan-950/40 to-emerald-950/40 border border-purple-500/30 shadow-xl flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider font-bold text-purple-300 flex items-center gap-1.5">
                  <GitMerge className="w-4 h-4 text-purple-400" />
                  Synthesized Champion Master Treatment
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-200 border border-purple-500/30 font-semibold">
                  Cross-Candidate Hybrid
                </span>
              </div>
              <p className="text-xs text-zinc-200 leading-relaxed">
                {synthesis.synthesis_rationale}
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-2 border-t border-white/10 text-xs">
                <div className="bg-black/40 p-2.5 rounded-lg border border-white/10 flex flex-col gap-1">
                  <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold">Hook Source</span>
                  <p className="text-amber-300 font-medium text-[11px]">{synthesis.hook_source_candidate}</p>
                </div>
                <div className="bg-black/40 p-2.5 rounded-lg border border-white/10 flex flex-col gap-1">
                  <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold">Core Story Arc</span>
                  <p className="text-purple-300 font-medium text-[11px]">{synthesis.core_narrative_source_candidate}</p>
                </div>
                <div className="bg-black/40 p-2.5 rounded-lg border border-white/10 flex flex-col gap-1">
                  <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold">Resolution Payoff</span>
                  <p className="text-emerald-300 font-medium text-[11px]">{synthesis.resolution_source_candidate}</p>
                </div>
              </div>
            </div>
          )}

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 bg-black/50 border border-white/10 rounded-xl flex flex-col gap-1">
              <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold flex items-center gap-1">
                <Target className="w-3 h-3 text-cyan-400" />
                Emotional Delta
              </span>
              <p className="text-xs text-cyan-300 font-mono font-medium">
                {intent?.core_emotional_transition || 'Narrative arc shift'}
              </p>
            </div>

            <div className="p-3 bg-black/50 border border-white/10 rounded-xl flex flex-col gap-1">
              <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold flex items-center gap-1">
                <Flame className="w-3 h-3 text-rose-400" />
                Core Conflict / Tension
              </span>
              <p className="text-xs text-zinc-200 line-clamp-2">
                {intent?.core_tension_or_conflict || 'Story conflict hook'}
              </p>
            </div>

            <div className="p-3 bg-black/50 border border-white/10 rounded-xl flex flex-col gap-1">
              <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold flex items-center gap-1">
                <Award className="w-3 h-3 text-emerald-400" />
                Winning Foundation
              </span>
              <p className="text-xs text-emerald-300 font-mono font-semibold">
                {selectedAngleId || 'alt_1'}
              </p>
            </div>
          </div>

          {/* Brief Directives & Revision Directives */}
          {decision?.revision_directives && decision.revision_directives.length > 0 && (
            <div className="p-3 bg-cyan-950/30 border border-cyan-500/30 rounded-xl flex flex-col gap-2">
              <span className="text-[10px] font-mono uppercase font-bold text-cyan-300">
                Director Revision Directives Applied to Final Cut:
              </span>
              <ul className="space-y-1 text-xs text-zinc-200">
                {decision.revision_directives.map((dir, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                    <span>{dir}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: STAGE 1 INTENT UNDERSTANDING */}
      {activeTab === 'intent' && intent && (
        <div className="flex flex-col gap-4 text-xs animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3.5 bg-black/50 border border-white/10 rounded-xl flex flex-col gap-1.5">
              <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold">Story Synopsis</span>
              <p className="text-zinc-200 leading-relaxed">{intent.story_summary}</p>
            </div>

            <div className="p-3.5 bg-black/50 border border-white/10 rounded-xl flex flex-col gap-1.5">
              <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold">Target Audience & Mindset</span>
              <p className="text-zinc-200 leading-relaxed">{intent.target_audience}</p>
            </div>

            <div className="p-3.5 bg-cyan-950/30 border border-cyan-500/30 rounded-xl flex flex-col gap-1.5">
              <span className="text-[10px] font-mono uppercase text-cyan-300 font-semibold flex items-center gap-1">
                <Compass className="w-3 h-3 text-cyan-400" />
                Audience Anticipation & Emotional Delta
              </span>
              <div className="space-y-1">
                <p className="font-mono text-cyan-200 font-medium">Delta: {intent.core_emotional_transition}</p>
                <p className="text-zinc-300 leading-relaxed">{intent.audience_anticipation}</p>
              </div>
            </div>

            <div className="p-3.5 bg-black/50 border border-white/10 rounded-xl flex flex-col gap-1.5">
              <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold">Authentic Voice & Perspective</span>
              <p className="text-zinc-200 leading-relaxed">{intent.authentic_voice_and_perspective}</p>
            </div>
          </div>

          {intent.production_constraints && intent.production_constraints.length > 0 && (
            <div className="p-3 bg-black/60 border border-white/10 rounded-xl flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-zinc-400 shrink-0" />
              <div className="flex flex-wrap gap-1.5 items-center">
                <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold mr-1">Constraints:</span>
                {intent.production_constraints.map((c, i) => (
                  <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-zinc-300">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: STAGE 2 MULTI-CANDIDATE GENERATION */}
      {activeTab === 'candidates' && (
        <div className="flex flex-col gap-4 animate-fade-in">
          <p className="text-xs text-zinc-400">
            The director generates 3 genuinely distinct narrative & visual candidates exploring divergent cinematic angles before judging.
          </p>

          <div className="grid grid-cols-1 gap-4">
            {alternatives.map((alt) => {
              const isSelected = selectedAngleId === alt.angle_id;
              const isExpanded = expandedCandidate === alt.angle_id;
              return (
                <div
                  key={alt.angle_id}
                  className={`p-4 rounded-xl border transition-all flex flex-col gap-3 ${
                    isSelected
                      ? 'bg-cyan-950/30 border-cyan-500/40 shadow-sm'
                      : 'bg-black/50 border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xs font-mono font-bold uppercase text-white">
                        {alt.title}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-zinc-300 border border-white/10">
                        {alt.angle_id}
                      </span>
                      {isSelected && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40">
                          Selected Foundation
                        </span>
                      )}
                    </div>

                    <button
                      onClick={() => setExpandedCandidate(isExpanded ? null : alt.angle_id)}
                      className="text-zinc-400 hover:text-white text-xs flex items-center gap-1 font-mono cursor-pointer"
                    >
                      <span>{isExpanded ? 'Less' : 'Details'}</span>
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  <p className="text-xs text-zinc-300 leading-relaxed font-normal">
                    {alt.angle_concept}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 bg-black/60 rounded-lg border border-white/10">
                      <span className="text-[9px] font-mono uppercase text-zinc-400 font-semibold block">Opening Hook & Unusual Moment</span>
                      <span className="text-zinc-200 text-[11px]">{alt.unusual_moments_or_hook}</span>
                    </div>
                    <div className="p-2.5 bg-black/60 rounded-lg border border-white/10">
                      <span className="text-[9px] font-mono uppercase text-zinc-400 font-semibold block">Emotional Subtext</span>
                      <span className="text-zinc-200 text-[11px]">{alt.emotional_core}</span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="flex flex-col gap-3 pt-3 border-t border-white/10 text-xs">
                      <div>
                        <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold block mb-1">Visual & Sound Strategy:</span>
                        <p className="text-zinc-300 leading-relaxed bg-black/60 p-2.5 rounded-lg border border-white/10">
                          {alt.visual_and_sound_strategy}
                        </p>
                      </div>

                      {alt.techniques_leveraged && alt.techniques_leveraged.length > 0 && (
                        <div>
                          <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold block mb-1.5">Leveraged Filmmaking Techniques:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {alt.techniques_leveraged.map((t, idx) => (
                              <span key={idx} className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                                ⚡ {t}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {alt.narrative_structure && alt.narrative_structure.length > 0 && (
                        <div>
                          <span className="text-[10px] font-mono uppercase text-zinc-400 font-semibold block mb-1">Narrative Beat Sequence:</span>
                          <div className="flex flex-wrap items-center gap-1.5 font-mono text-[10px]">
                            {alt.narrative_structure.map((beat, bIdx) => (
                              <React.Fragment key={bIdx}>
                                <span className="px-2 py-0.5 rounded bg-white/5 text-zinc-200 border border-white/10">
                                  {beat}
                                </span>
                                {bIdx < (alt.narrative_structure?.length || 0) - 1 && (
                                  <span className="text-zinc-500">➔</span>
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 4: STAGE 3 STRUCTURED JUDGE & HYBRID SYNTHESIS */}
      {activeTab === 'judge' && (
        <div className="flex flex-col gap-5 text-xs animate-fade-in">
          {/* Hybrid Synthesis Highlight */}
          {isHybrid && (
            <div className="p-4 bg-purple-950/40 border border-purple-500/30 rounded-xl flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold uppercase text-purple-300 flex items-center gap-1.5">
                  <GitMerge className="w-4 h-4 text-purple-400" />
                  Hybrid Cross-Pollination Synthesis
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-200 border border-purple-500/30 font-bold">
                  Superior Combinatorial Edit
                </span>
              </div>
              <p className="text-xs text-zinc-300 leading-relaxed">
                Rather than discarding weaker candidates entirely, the structured judge extracted the winning elements from each direction and synthesized them into an optimal master cut.
              </p>
              {synthesis && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs pt-1">
                  <div className="bg-black/60 p-2.5 rounded-lg border border-white/10">
                    <span className="text-[9px] font-mono uppercase text-zinc-400 block">Hook Component</span>
                    <span className="font-semibold text-purple-300">{synthesis.hook_source_candidate}</span>
                  </div>
                  <div className="bg-black/60 p-2.5 rounded-lg border border-white/10">
                    <span className="text-[9px] font-mono uppercase text-zinc-400 block">Narrative Core</span>
                    <span className="font-semibold text-purple-300">{synthesis.core_narrative_source_candidate}</span>
                  </div>
                  <div className="bg-black/60 p-2.5 rounded-lg border border-white/10">
                    <span className="text-[9px] font-mono uppercase text-zinc-400 block">Resolution Payoff</span>
                    <span className="font-semibold text-purple-300">{synthesis.resolution_source_candidate}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Candidate Evaluation Scorecards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {evaluations.map((ev) => {
              const isSelected = selectedAngleId === ev.angle_id;
              const crit = ev.criteria;
              return (
                <div
                  key={ev.angle_id}
                  className={`p-3.5 rounded-xl border flex flex-col justify-between gap-3 ${
                    isSelected
                      ? 'bg-cyan-950/30 border-cyan-500/40 shadow-sm'
                      : 'bg-black/50 border-white/10'
                  }`}
                >
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-white uppercase">
                        {ev.angle_id}
                      </span>
                      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-white/5 text-zinc-200 border border-white/10">
                        {ev.total_score ? `${ev.total_score.toFixed(1)}/50` : 'Rated'}
                      </span>
                    </div>

                    {/* Criteria Bars */}
                    {crit && (
                      <div className="space-y-1.5 pt-1 font-mono text-[10px]">
                        <div>
                          <div className="flex justify-between text-zinc-400 mb-0.5">
                            <span>Originality</span>
                            <span className="font-bold text-white">{crit.originality.toFixed(1)}</span>
                          </div>
                          <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                            <div className="bg-purple-500 h-full rounded-full" style={{ width: `${(crit.originality / 10) * 100}%` }} />
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-zinc-400 mb-0.5">
                            <span>Clarity</span>
                            <span className="font-bold text-white">{crit.clarity.toFixed(1)}</span>
                          </div>
                          <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                            <div className="bg-cyan-400 h-full rounded-full" style={{ width: `${(crit.clarity / 10) * 100}%` }} />
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-zinc-400 mb-0.5">
                            <span>Emotional Impact</span>
                            <span className="font-bold text-white">{crit.emotional_impact.toFixed(1)}</span>
                          </div>
                          <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                            <div className="bg-rose-500 h-full rounded-full" style={{ width: `${(crit.emotional_impact / 10) * 100}%` }} />
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-zinc-400 mb-0.5">
                            <span>Feasibility</span>
                            <span className="font-bold text-white">{crit.feasibility.toFixed(1)}</span>
                          </div>
                          <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                            <div className="bg-amber-400 h-full rounded-full" style={{ width: `${(crit.feasibility / 10) * 100}%` }} />
                          </div>
                        </div>

                        <div>
                          <div className="flex justify-between text-zinc-400 mb-0.5">
                            <span>Fit to Creator</span>
                            <span className="font-bold text-white">{crit.fit_to_creator_intent.toFixed(1)}</span>
                          </div>
                          <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                            <div className="bg-emerald-400 h-full rounded-full" style={{ width: `${(crit.fit_to_creator_intent / 10) * 100}%` }} />
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Verdict Quote */}
                    {ev.judge_verdict && (
                      <p className="text-[11px] text-zinc-300 italic pt-2 border-t border-white/10 leading-relaxed">
                        "{ev.judge_verdict}"
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Judge Selection Rationale */}
          {decision?.selection_rationale && (
            <div className="p-3.5 bg-black/60 border border-white/10 rounded-xl flex flex-col gap-1.5">
              <span className="text-[10px] font-mono uppercase font-bold text-zinc-400">
                Judge Foundation Rationale:
              </span>
              <p className="text-zinc-200 leading-relaxed">
                {decision.selection_rationale}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
