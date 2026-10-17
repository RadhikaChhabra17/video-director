import React, { useState, useEffect } from 'react';
import { DirectRequest } from '../types/director';
import { Sparkles, Film, Clock, ArrowRight, Sliders, Compass } from 'lucide-react';

interface PromptPanelProps {
  onDirect: (params: DirectRequest) => Promise<void>;
  isLoading: boolean;
  initialScript?: string;
  initialDuration?: number;
  initialCategory?: string;
  referenceTitle?: string;
  referenceVideoId?: string;
  activeDirectionTag?: string;
  onScriptChange?: (newScript: string) => void;
  onDurationChange?: (newDuration: number) => void;
}

export const PromptPanel: React.FC<PromptPanelProps> = ({
  onDirect,
  isLoading,
  initialScript,
  initialDuration,
  initialCategory,
  referenceTitle,
  referenceVideoId,
  activeDirectionTag,
  onScriptChange,
  onDurationChange,
}) => {
  const [script, setScript] = useState<string>(
    initialScript !== undefined
      ? initialScript
      : 'First time trying authentic South Indian filter coffee pulled between brass cups in Bangalore cafe. Pure adrenaline, steam, and strong chicory.'
  );
  const [duration, setDuration] = useState<number>(initialDuration || 10.0);

  useEffect(() => {
    if (initialScript !== undefined) {
      setScript(initialScript);
    }
  }, [initialScript]);

  useEffect(() => {
    if (initialDuration !== undefined) {
      setDuration(initialDuration);
    }
  }, [initialDuration]);

  const durationOptions = [
    { value: 10, label: '10s', desc: 'Omni Reference Video' },
    { value: 12, label: '12s', desc: 'Travel Beat' },
    { value: 15, label: '15s', desc: 'Story Arc' },
    { value: 20, label: '20s', desc: 'Extended' },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!script.trim() || isLoading) return;
    onDirect({
      script,
      duration,
      category: initialCategory,
      reference_video_id: referenceVideoId,
      active_direction_tag: activeDirectionTag,
    });
  };

  return (
    <div className="glass-hud rounded-3xl p-6 sm:p-7 flex flex-col gap-6 shadow-2xl border border-white/10 relative overflow-hidden backdrop-blur-2xl text-white">
      {/* Decorative accent bar */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-400 via-teal-400 to-lime-300"></div>

      {/* Header */}
      <div>
        <div className="flex items-center gap-1.5 mb-1.5">
          <span className="w-5 h-5 rounded-md bg-cyan-500/15 border border-cyan-400/30 flex items-center justify-center text-cyan-400">
            <Film className="w-3 h-3 text-cyan-400" />
          </span>
          <span className="text-[10px] uppercase font-mono tracking-widest text-cyan-400 font-bold">
            DIRECTOR MODE // BRIEFING
          </span>
        </div>
        <h2 className="text-xl font-extrabold text-white tracking-tight">Prompt & Creative Pitch</h2>
        <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
          Input your script or story concept. The director agent will formulate the visual language, camera movements, audio cues, and shot plan.
        </p>
      </div>

      {referenceTitle && (
        <div className="bg-cyan-500/10 border border-cyan-400/30 rounded-2xl p-3.5 flex items-start gap-3 shadow-xs animate-fade-in">
          <div className="w-7 h-7 rounded-lg bg-cyan-500/20 flex items-center justify-center shrink-0 text-cyan-400 mt-0.5 border border-cyan-400/40">
            <Sliders className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] uppercase font-mono tracking-wider font-bold text-cyan-300">
                Active Style Transfer Source
              </span>
              {activeDirectionTag && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-400/20 text-cyan-200 border border-cyan-400/30 font-mono">
                  <Compass className="w-2.5 h-2.5 text-cyan-400" />
                  Modifier: {activeDirectionTag}
                </span>
              )}
            </div>
            <p className="text-xs font-bold text-white truncate mt-0.5">
              "{referenceTitle}"
            </p>
            <p className="text-[11px] text-zinc-400 mt-0.5 leading-tight">
              Inheriting deconstructed editing cadence, hook timing, and visual staging invariants.
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {/* Script / Core Idea Input */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-300 font-semibold">
              Script or Story Concept
            </label>
            <span className="text-[10px] font-mono text-zinc-500">
              {script.length} characters
            </span>
          </div>
          <div className="relative">
            <textarea
              rows={5}
              value={script}
              onChange={(e) => {
                setScript(e.target.value);
                onScriptChange?.(e.target.value);
              }}
              disabled={isLoading}
              placeholder="e.g. Creator explores hidden rooftop sunrise spot in Tokyo, chaotic morning commuter crowds transition to total zen stillness..."
              className="w-full bg-black/60 border border-white/10 rounded-2xl p-3.5 text-xs font-mono text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/40 leading-relaxed custom-scroll transition-all resize-none"
            />
          </div>
        </div>

        {/* Target Duration Selector Pills */}
        <div className="flex flex-col gap-2">
          <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-300 font-semibold flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Target Duration</span>
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {durationOptions.map((opt) => {
              const isSelected = duration === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    setDuration(opt.value);
                    onDurationChange?.(opt.value);
                  }}
                  disabled={isLoading}
                  className={`py-2 px-2 sm:px-2.5 rounded-xl border text-center transition-all flex flex-col items-center justify-center cursor-pointer ${
                    isSelected
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400/50 shadow-[0_0_12px_rgba(0,240,255,0.15)] font-bold scale-[1.02]'
                      : 'bg-black/40 hover:bg-white/5 text-zinc-400 hover:text-zinc-200 border-white/10 font-medium'
                  }`}
                >
                  <span className="text-xs font-mono font-bold leading-tight">{opt.label}</span>
                  <span className={`text-[9px] font-sans mt-0.5 leading-tight ${isSelected ? 'text-cyan-200/80' : 'text-zinc-500'}`}>
                    {opt.desc}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Submit Action Button */}
        <button
          type="submit"
          disabled={isLoading || !script.trim()}
          className="w-full mt-1 py-3.5 rounded-xl text-xs font-bold bg-gradient-to-r from-lime-300 to-emerald-300 hover:brightness-110 text-black tracking-wider shadow-lg shadow-lime-300/20 active:scale-[0.99] group cursor-pointer transition-all flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
              <span className="font-mono">Directing Cut with Gemini...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-black group-hover:rotate-12 transition-transform" />
              <span className="tracking-wider">BUILD SHOT PLAN [ ↗ ]</span>
              <ArrowRight className="w-3.5 h-3.5 text-black group-hover:translate-x-0.5 transition-transform" />
            </>
          )}
        </button>
      </form>
    </div>
  );
};
