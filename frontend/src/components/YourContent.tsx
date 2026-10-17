import React from 'react';
import { Layers, Clock, ArrowRight } from 'lucide-react';
import { ManifestSummary } from '../types/director';

interface YourContentProps {
  manifests: ManifestSummary[];
  onOpenDirector: (filename: string) => void;
}

export const YourContent: React.FC<YourContentProps> = ({ manifests, onOpenDirector }) => {
  return (
    <div className="flex-1 overflow-y-auto custom-scroll p-6 lg:p-8 flex flex-col gap-6">
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div>
          <span className="text-xs uppercase font-mono tracking-widest text-pink-400 font-bold flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-pink-400" />
            Project Archive
          </span>
          <h1 className="text-xl font-bold text-white mt-0.5 tracking-tight">Your Content & Directed Manifests</h1>
          <p className="text-xs text-zinc-400 mt-1">
            All stored Director response manifests ready for editing or production rendering.
          </p>
        </div>
        <span className="text-xs font-mono px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-zinc-300 shadow-sm">
          {manifests.length} Active Projects
        </span>
      </div>

      {manifests.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 bg-[#080a10]/70 glass-hud rounded-3xl border border-white/10 text-center gap-4 my-8 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-pink-500/15 text-pink-400 flex items-center justify-center border border-pink-500/30 shadow-[0_0_15px_rgba(244,63,94,0.2)]">
            <Layers className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">No session projects yet</h3>
            <p className="text-xs text-zinc-400 mt-1 max-w-md">
              Projects directed or saved in this browser session will appear here with complete shot manifests.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {manifests.map((m) => (
          <div
            key={m.filename}
            className="bg-[#080a10]/80 glass-hud border border-white/10 hover:border-pink-500/40 rounded-2xl p-6 flex flex-col justify-between gap-5 transition-all group shadow-xl hover:shadow-[0_8px_30px_rgba(244,63,94,0.15)]"
          >
            <div className="flex flex-col gap-2.5">
              <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
                <span className="text-pink-400 font-bold">{m.project_id}</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-pink-400" />
                  {m.total_target_duration_sec}s
                </span>
              </div>
              <h3 className="text-sm font-bold text-white leading-snug group-hover:text-pink-300 transition-colors">
                {m.title}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-zinc-300 border border-white/10">
                  {m.shots_count} Shots
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-zinc-300 border border-white/10">
                  {m.aspect_ratio}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end pt-4 border-t border-white/10">
              <button
                onClick={() => onOpenDirector(m.filename)}
                className="px-3 py-1.5 rounded-lg text-xs font-bold bg-gradient-to-r from-lime-300 to-emerald-300 text-black border border-lime-300/40 hover:brightness-110 active:scale-95 transition-all flex items-center gap-1.5 shadow-[0_0_12px_rgba(190,242,100,0.25)] cursor-pointer"
              >
                <span>View in Director</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
        </div>
      )}
    </div>
  );
};
