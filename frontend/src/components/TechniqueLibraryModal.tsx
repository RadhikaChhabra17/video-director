import React, { useState } from 'react';
import { TechniqueRecord } from '../types/director';
import {
  Sparkles,
  Search,
  CheckCircle,
  XCircle,
  RefreshCw,
  Video,
  Scissors,
  Layers,
  Volume2,
} from 'lucide-react';

interface TechniqueLibraryModalProps {
  isOpen: boolean;
  onClose: () => void;
  techniques: TechniqueRecord[];
  onIngest: () => Promise<void>;
  isIngesting: boolean;
}

export const TechniqueLibraryModal: React.FC<TechniqueLibraryModalProps> = ({
  isOpen,
  onClose,
  techniques,
  onIngest,
  isIngesting,
}) => {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedTechnique, setSelectedTechnique] = useState<TechniqueRecord | null>(null);

  if (!isOpen) return null;

  const filtered = techniques.filter((t) => {
    const matchesCat = selectedCategory === 'all' || t.category === selectedCategory;
    const matchesSearch =
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.technique_id.toLowerCase().includes(search.toLowerCase()) ||
      t.core_mechanism.toLowerCase().includes(search.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'camera':
        return <Video className="w-3.5 h-3.5 text-amber-600" />;
      case 'editing':
        return <Scissors className="w-3.5 h-3.5 text-sky-600" />;
      case 'visual_storytelling':
        return <Layers className="w-3.5 h-3.5 text-purple-600" />;
      case 'sound_rhythm':
        return <Volume2 className="w-3.5 h-3.5 text-emerald-600" />;
      default:
        return <Sparkles className="w-3.5 h-3.5 text-amber-600" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in">
      <div className="bg-[#080a10]/95 glass-hud border border-white/10 rounded-3xl w-full max-w-5xl h-[85vh] shadow-2xl flex flex-col overflow-hidden">
        
        {/* Modal Header */}
        <div className="px-4 sm:px-6 py-4 sm:py-5 border-b border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-black/40">
          <div className="flex items-center gap-3">
            <span className="w-9 h-9 rounded-xl bg-cyan-500/15 text-cyan-400 flex items-center justify-center font-bold border border-cyan-500/30 shadow-sm shrink-0">
              <Sparkles className="w-5 h-5 text-cyan-400" />
            </span>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-bold text-white tracking-tight">Canonical Filmmaking Technique Library</h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 font-bold border border-cyan-500/30">
                  {techniques.length} Techniques
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-0.5">
                Curated camera movements, editing cuts, visual cues, and sound rhythms powering the AI Director.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 self-end sm:self-auto">
            <button
              onClick={onIngest}
              disabled={isIngesting}
              className="px-3.5 py-1.5 rounded-xl text-xs font-mono font-semibold bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-200 shadow-sm flex items-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer"
              title="Rescan corpus/data/*.json and update evidence counts"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${isIngesting ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{isIngesting ? 'Ingesting Dataset...' : 'Re-ingest Dataset'}</span>
              <span className="sm:hidden">{isIngesting ? 'Ingesting...' : 'Re-ingest'}</span>
            </button>

            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white flex items-center justify-center text-sm font-bold transition-colors cursor-pointer border border-white/10"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Search & Category Filter Toolbar */}
        <div className="px-4 sm:px-6 py-3 border-b border-white/10 bg-black/30 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search techniques, mechanisms..."
              className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-white/10 text-xs font-mono focus:outline-none focus:border-cyan-400 bg-black/60 text-white placeholder-zinc-500 shadow-inner"
            />
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
            {['all', 'camera', 'editing', 'visual_storytelling', 'sound_rhythm'].map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-xl text-xs font-mono capitalize transition-all whitespace-nowrap cursor-pointer ${
                  selectedCategory === cat
                    ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40 shadow-sm'
                    : 'bg-white/5 text-zinc-400 border border-white/10 hover:text-white hover:bg-white/10'
                }`}
              >
                {cat.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Modal Main Content: 2-Column Split */}
        <div className="flex-1 overflow-hidden grid grid-cols-12">
          
          {/* Technique Cards List */}
          <div className="col-span-12 md:col-span-6 overflow-y-auto custom-scroll p-4 sm:p-6 border-b md:border-b-0 md:border-r border-white/10 flex flex-col gap-3 bg-black/20">
            {filtered.map((t) => {
              const isSelected = selectedTechnique?.technique_id === t.technique_id;
              return (
                <div
                  key={t.technique_id}
                  onClick={() => setSelectedTechnique(t)}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all flex flex-col gap-2 ${
                    isSelected
                      ? 'bg-cyan-950/40 border-cyan-500/50 shadow-lg text-white'
                      : 'bg-[#0b0e17]/80 border-white/10 hover:border-cyan-400/40 hover:bg-black/40 text-white'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="p-1 rounded-md bg-white/5 border border-white/10">
                        {getCategoryIcon(t.category)}
                      </span>
                      <span className="font-bold text-xs text-white">{t.name}</span>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500">
                      {t.evidence_count || 1} evidence
                    </span>
                  </div>

                  <p className="text-xs text-zinc-300 line-clamp-2 leading-relaxed">
                    {t.core_mechanism}
                  </p>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-zinc-400 border border-white/10">
                      {t.technique_id}
                    </span>
                    <span className="text-[10px] font-mono text-cyan-300 font-semibold">
                      {t.use_when?.length || 0} trigger rules
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Technique Detailed Inspector */}
          <div className="col-span-12 md:col-span-6 overflow-y-auto custom-scroll p-4 sm:p-6 bg-black/40 flex flex-col justify-between">
            {selectedTechnique ? (
              <div className="flex flex-col gap-5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-cyan-500/15 border border-cyan-500/30">
                      {getCategoryIcon(selectedTechnique.category)}
                    </span>
                    <div>
                      <h4 className="text-base font-bold text-white">{selectedTechnique.name}</h4>
                      <span className="text-[10px] font-mono text-cyan-400 uppercase">{selectedTechnique.technique_id}</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-black/60 rounded-2xl border border-white/10 flex flex-col gap-1.5 shadow-inner">
                  <span className="text-[10px] font-mono uppercase text-zinc-400 font-bold">Core Mechanism & What Happens</span>
                  <p className="text-xs text-zinc-200 leading-relaxed font-normal">
                    {selectedTechnique.core_mechanism}
                  </p>
                </div>

                {/* When to use */}
                <div className="p-4 bg-emerald-950/30 rounded-2xl border border-emerald-500/30 flex flex-col gap-2">
                  <span className="text-[10px] font-mono uppercase text-emerald-300 font-bold flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    When To Apply In Short-Form Cuts
                  </span>
                  <ul className="space-y-1.5 text-xs text-emerald-200">
                    {(selectedTechnique.use_when || []).map((rule, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-emerald-400 font-bold">•</span>
                        <span>{rule}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* When to avoid */}
                <div className="p-4 bg-rose-950/30 rounded-2xl border border-rose-500/30 flex flex-col gap-2">
                  <span className="text-[10px] font-mono uppercase text-rose-300 font-bold flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5 text-rose-400" />
                    When To Avoid
                  </span>
                  <ul className="space-y-1.5 text-xs text-rose-200">
                    {(selectedTechnique.avoid_when || []).map((rule, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-rose-400 font-bold">•</span>
                        <span>{rule}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Variants if present */}
                {selectedTechnique.variants && Object.keys(selectedTechnique.variants).length > 0 && (
                  <div className="p-4 bg-black/60 rounded-2xl border border-white/10 flex flex-col gap-2 shadow-inner">
                    <span className="text-[10px] font-mono uppercase text-zinc-400 font-bold">Execution Variants</span>
                    <div className="grid grid-cols-1 gap-2 text-xs">
                      {Object.entries(selectedTechnique.variants).map(([vName, vDesc]) => (
                        <div key={vName} className="p-2.5 rounded-xl bg-white/5 border border-white/10 flex flex-col gap-0.5">
                          <span className="font-mono font-bold text-amber-300 capitalize text-[11px]">{vName.replace(/_/g, ' ')}</span>
                          <span className="text-zinc-300 text-[11px]">{vDesc}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-8">
                <Sparkles className="w-8 h-8 text-cyan-400 mb-2 opacity-60" />
                <h5 className="text-xs font-mono font-bold text-white uppercase">Select a Technique</h5>
                <p className="text-xs text-zinc-400 mt-1 max-w-xs">
                  Click any canonical technique on the left to inspect its trigger rules, avoidance criteria, and execution mechanics.
                </p>
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
};
