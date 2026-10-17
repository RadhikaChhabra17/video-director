import React, { useState } from 'react';
import { DirectorShotPlan } from '../types/director';
import { Sparkles, Trash2, Clock, Video, Volume2, Mic } from 'lucide-react';

interface ShotCardProps {
  shot: DirectorShotPlan;
  index: number;
  onUpdate: (updated: DirectorShotPlan) => void;
  onDelete: () => void;
  onRefineChat: (instruction: string) => Promise<string | void>;
  isRefining: boolean;
}

export const ShotCard: React.FC<ShotCardProps> = ({
  shot,
  index,
  onUpdate,
  onDelete,
  onRefineChat,
  isRefining,
}) => {
  const [chatInput, setChatInput] = useState('');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [directorRationale, setDirectorRationale] = useState<string | null>(null);

  const handleDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const dur = parseFloat(e.target.value) || 0.5;
    onUpdate({ ...shot, duration_sec: dur });
  };

  const handleVisualChange = (field: string, value: string) => {
    onUpdate({
      ...shot,
      visual: {
        ...shot.visual,
        [field]: value,
      },
    });
  };

  const handleTranscriptChange = (val: string) => {
    onUpdate({
      ...shot,
      audio: {
        ...shot.audio,
        speech: {
          ...shot.audio?.speech,
          transcript: val,
        },
      },
    });
  };

  const handleSfxChange = (val: string) => {
    const cues = val.split(',').map((s) => ({
      sfx_name: s.trim(),
      trigger_offset_sec: 0.0,
      volume_db: -2.0,
    })).filter((c) => c.sfx_name.length > 0);

    onUpdate({
      ...shot,
      audio: {
        ...shot.audio,
        sfx_cues: cues,
      },
    });
  };

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isRefining) return;
    const rationale = await onRefineChat(chatInput.trim());
    if (typeof rationale === 'string' && rationale.trim().length > 0) {
      setDirectorRationale(rationale);
    }
    setChatInput('');
  };

  const sfxString = (shot.audio?.sfx_cues || []).map((c) => c.sfx_name).join(', ');

  return (
    <div className="bg-[#0b0e17]/90 glass-hud border border-white/10 hover:border-cyan-400/40 rounded-2xl p-5 flex flex-col gap-4 transition-all shadow-xl group">
      
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-white/10 pb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-2.5 py-1 rounded-lg bg-cyan-500/10 text-cyan-400 font-mono text-xs font-bold border border-cyan-500/30 shadow-[0_0_10px_rgba(0,240,255,0.15)]">
            Shot {index + 1}
          </span>
          {shot.beat_name && (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-white/5 text-zinc-300 border border-white/10 uppercase tracking-wider">
              {shot.beat_name}
            </span>
          )}
          {shot.is_hook_critical && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-pink-500/15 text-pink-300 border border-pink-500/30 font-semibold shadow-[0_0_8px_rgba(244,63,94,0.2)]">
              Hook Critical
            </span>
          )}
        </div>

        <div className="flex items-center gap-2.5 self-end sm:self-auto">
          <div className="flex items-center gap-1.5 font-mono text-xs bg-black/60 border border-white/10 rounded-lg px-2.5 py-1 text-zinc-300">
            <Clock className="w-3.5 h-3.5 text-zinc-400" />
            <input
              type="number"
              step="0.1"
              min="0.5"
              max="10.0"
              value={shot.duration_sec}
              onChange={handleDurationChange}
              className="w-11 text-center text-cyan-300 font-bold focus:outline-none bg-transparent"
            />
            <span className="text-zinc-500 text-[11px]">s</span>
          </div>

          <button
            onClick={() => setIsChatOpen(!isChatOpen)}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all border cursor-pointer ${
              isChatOpen
                ? 'bg-cyan-500/20 text-cyan-200 border-cyan-400 font-bold shadow-[0_0_10px_rgba(0,240,255,0.2)]'
                : 'bg-white/5 hover:bg-white/10 text-zinc-300 border-white/10'
            }`}
            title="Refine this shot with AI"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>Refine</span>
          </button>

          <button
            onClick={onDelete}
            className="text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors p-1.5 rounded-lg cursor-pointer"
            title="Delete Shot"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Visual Scene Description */}
      <div className="flex flex-col gap-1.5">
        <label className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5 font-semibold">
          <Video className="w-3 h-3 text-cyan-400" />
          Scene Description
        </label>
        <textarea
          rows={2}
          value={shot.visual?.scene_description || ''}
          onChange={(e) => handleVisualChange('scene_description', e.target.value)}
          className="w-full bg-black/60 border border-white/10 rounded-xl p-3 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-cyan-400 focus:bg-black/80 leading-relaxed custom-scroll font-sans transition-colors"
        />
      </div>

      {/* Subject Action & Optics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold">Subject Action</label>
          <input
            type="text"
            value={shot.visual?.subject_action || ''}
            onChange={(e) => handleVisualChange('subject_action', e.target.value)}
            className="bg-black/60 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-cyan-400 focus:bg-black/80 font-mono transition-colors"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold">Camera Framing & Movement</label>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="cu / wide / pov"
              value={shot.visual?.framing || 'cu'}
              onChange={(e) => handleVisualChange('framing', e.target.value)}
              className="w-1/2 bg-black/60 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:border-cyan-400 focus:bg-black/80"
            />
            <input
              type="text"
              placeholder="handheld / zoom"
              value={shot.visual?.camera_movement || 'handheld'}
              onChange={(e) => handleVisualChange('camera_movement', e.target.value)}
              className="w-1/2 bg-black/60 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:border-cyan-400 focus:bg-black/80"
            />
          </div>
        </div>
      </div>

      {/* Dialogue and SFX */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-white/10">
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5 font-semibold">
            <Mic className="w-3 h-3 text-amber-400" />
            Spoken Dialogue / Transcript
          </label>
          <input
            type="text"
            value={shot.audio?.speech?.transcript || ''}
            onChange={(e) => handleTranscriptChange(e.target.value)}
            className="bg-black/60 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-amber-300 font-mono focus:outline-none focus:border-amber-400 focus:bg-black/80"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5 font-semibold">
            <Volume2 className="w-3 h-3 text-cyan-400" />
            Ambient SFX Cues (comma-separated)
          </label>
          <input
            type="text"
            placeholder="whoosh, pour, hit"
            value={sfxString}
            onChange={(e) => handleSfxChange(e.target.value)}
            className="bg-black/60 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-cyan-300 font-mono focus:outline-none focus:border-cyan-400 focus:bg-black/80"
          />
        </div>
      </div>

      {/* Applied Filmmaking Techniques */}
      {shot.applied_techniques && shot.applied_techniques.length > 0 && (
        <div className="flex items-center gap-2 pt-1 border-t border-white/5 flex-wrap">
          <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-semibold">
            Techniques:
          </span>
          <div className="flex items-center gap-1.5 flex-wrap">
            {shot.applied_techniques.map((tId) => (
              <span
                key={tId}
                className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-medium capitalize"
                title={`Applied Filmmaking Technique: ${tId}`}
              >
                ⚡ {tId.split('.').pop()?.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Per-Shot Chat Refinement Experience */}
      {isChatOpen && (
        <form onSubmit={handleChatSubmit} className="mt-1 p-3.5 bg-black/70 rounded-xl border border-cyan-500/30 flex flex-col gap-2.5 backdrop-blur-md shadow-inner">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-cyan-300 font-semibold flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              Direct this shot via natural language:
            </span>
            {isRefining && (
              <span className="text-[10px] font-mono text-cyan-400 animate-pulse font-medium">
                AI Director refining shot...
              </span>
            )}
          </div>

          {directorRationale && (
            <div className="p-2.5 bg-cyan-950/40 border border-cyan-500/40 rounded-lg text-xs text-cyan-200 font-mono flex items-start gap-2 shadow-sm">
              <span className="font-bold text-cyan-400 shrink-0">Director Note:</span>
              <span className="italic leading-relaxed">{directorRationale}</span>
            </div>
          )}

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={chatInput}
              disabled={isRefining}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="e.g. Change camera to sudden whip pan, add whoosh sound, make reaction more shocked..."
              className="flex-1 bg-black/80 border border-white/10 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-cyan-400 font-mono shadow-inner"
            />
            <button
              type="submit"
              disabled={isRefining || !chatInput.trim()}
              className="px-4 py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-lime-300 to-emerald-300 text-black border border-lime-300/40 hover:brightness-110 active:scale-95 transition-all shadow-[0_0_15px_rgba(190,242,100,0.25)] disabled:opacity-50 cursor-pointer shrink-0"
            >
              Refine Shot
            </button>
          </div>
        </form>
      )}

    </div>
  );
};

