import React from 'react';
import { Film, Eye, Sparkles, Video, ArrowRight, CheckCircle2, Zap, ShieldCheck, Flame } from 'lucide-react';

interface FeatureScrollSectionProps {
  onScrollDown: () => void;
  onLaunchStudio: (module: 'director' | 'analyser' | 'content' | 'library') => void;
}

export const FeatureScrollSection: React.FC<FeatureScrollSectionProps> = ({
  onScrollDown,
  onLaunchStudio,
}) => {
  return (
    <div className="relative z-10 flex flex-col w-full max-w-7xl mx-auto">
      {/* ------------------------------------------------------------- */}
      {/* SECTION 0: HERO INTRO */}
      {/* ------------------------------------------------------------- */}
      <section
        id="stage-0"
        className="min-h-screen flex flex-col items-center justify-between py-28 px-6 text-center"
      >
        <div className="flex flex-col items-center gap-5 mt-6 animate-fade-in max-w-4xl">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 shadow-lg text-xs font-mono text-zinc-300 backdrop-blur-md">
            <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse"></span>
            <span>Gemini 3.8 Flash Engine</span>
          </div>

          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold text-white tracking-tight leading-[1.08]">
            Where your footage becomes the{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-lime-300 underline decoration-cyan-400/50 decoration-wavy">
              living canvas
            </span>
            .
          </h1>

          <p className="text-base sm:text-lg text-zinc-300 max-w-2xl leading-relaxed">
            An autonomous creative intelligence studio for viral Shorts. Decompile outlier retention patterns, direct per-shot cinematic blueprints, and synthesize consistent character reference videos.
          </p>

          <div className="flex items-center gap-3.5 flex-wrap justify-center mt-3">
            <button
              onClick={() => onLaunchStudio('director')}
              className="px-6 py-3.5 rounded-2xl text-sm font-bold bg-gradient-to-r from-lime-300 to-emerald-300 text-black border border-lime-300/40 hover:brightness-110 active:scale-95 shadow-[0_0_20px_rgba(190,242,100,0.3)] transition-all flex items-center gap-2.5 cursor-pointer"
            >
              <span>Launch AI Director</span>
              <ArrowRight className="w-4 h-4 text-black" />
            </button>

            <button
              onClick={onScrollDown}
              className="px-6 py-3.5 rounded-2xl text-sm font-semibold bg-white/5 hover:bg-white/10 text-white border border-white/10 shadow-sm transition-all flex items-center gap-2 active:scale-95 cursor-pointer backdrop-blur-md"
            >
              <span>Explore Features</span>
              <ArrowRight className="w-4 h-4 text-zinc-400" />
            </button>
          </div>

          {/* Feature Badges */}
          <div className="flex items-center gap-2 sm:gap-4 flex-wrap justify-center mt-4 text-[11px] font-mono text-zinc-300">
            <span className="px-3 py-1 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 shadow-sm">
              ⚡ Gemini 3.8 Flash
            </span>
            <span className="px-3 py-1 rounded-lg bg-purple-500/10 text-purple-300 border border-purple-500/20 shadow-sm">
              📊 Multimodal Video Telemetry
            </span>
            <span className="px-3 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/20 shadow-sm">
              🔥 Outlier Hook Formulas
            </span>
            <span className="px-3 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 shadow-sm">
              🎬 AI Reference Video
            </span>
          </div>
        </div>

        {/* Scroll Indicator */}
        <div
          onClick={onScrollDown}
          className="flex flex-col items-center gap-2 text-zinc-400 text-xs font-mono mb-4 animate-pulse cursor-pointer hover:text-white transition-colors"
        >
          <span>SCROLL TO EXPLORE</span>
          <div className="w-5 h-8 rounded-full border-2 border-white/20 flex items-start justify-center p-1">
            <div className="w-1.5 h-2 bg-cyan-400 rounded-full animate-bounce"></div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 1: AI DIRECTOR */}
      {/* ------------------------------------------------------------- */}
      <section
        id="stage-1"
        className="min-h-screen flex items-center justify-center p-6 sm:p-12"
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center w-full">
          {/* Narrative Card */}
          <div className="lg:col-span-5 flex flex-col gap-4 bg-[#080a10]/80 glass-hud border border-white/10 rounded-3xl p-8 shadow-2xl">
            <div className="flex items-center justify-between">
              <span className="px-3 py-1 rounded-full text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                01 // AI DIRECTOR
              </span>
              <div className="w-8 h-8 rounded-xl bg-cyan-500/15 flex items-center justify-center text-cyan-400 border border-cyan-500/30">
                <Film className="w-4 h-4" />
              </div>
            </div>

            <h2 className="text-3xl font-bold text-white tracking-tight">
              Natural Language to Per-Shot Production Blueprint
            </h2>

            <p className="text-xs text-zinc-300 leading-relaxed">
              Input a rough idea or topic. The director agent formulates camera choreography, lens focal lengths, lighting palettes, voiceover transcripts, and precise sound design cues per cut.
            </p>

            <div className="space-y-2.5 pt-2 border-t border-white/10 text-xs text-zinc-300">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>Multi-candidate angle generation with judge scoring</span>
              </div>
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>Per-shot interactive refiner chat powered by Gemini 3.8 Flash</span>
              </div>
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>Precise audio foley cues with volume & trigger offsets</span>
              </div>
            </div>

            <button
              onClick={() => onLaunchStudio('director')}
              className="mt-3 w-full py-3 rounded-xl bg-gradient-to-r from-cyan-400 to-teal-400 text-black font-bold text-xs transition-all flex items-center justify-center gap-2 shadow-lg shadow-cyan-400/20 hover:brightness-110 active:scale-98 cursor-pointer"
            >
              <span>Open AI Director Studio</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Live UI Mockup Card */}
          <div className="lg:col-span-7 bg-[#0b0e17]/90 glass-hud border border-white/10 rounded-3xl p-6 sm:p-7 shadow-2xl flex flex-col gap-5 text-zinc-200">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-500/80"></span>
                <span className="w-3 h-3 rounded-full bg-amber-500/80"></span>
                <span className="w-3 h-3 rounded-full bg-emerald-500/80"></span>
                <span className="text-xs font-mono text-zinc-400 ml-2">production_manifest.json</span>
              </div>
              <span className="text-[11px] font-mono text-cyan-300 bg-cyan-500/15 px-2.5 py-0.5 rounded-full border border-cyan-500/30">
                10.0s Target
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { id: 'SHOT 01', beat: 'Hook', time: '2.0s', optics: '18mm Wide Macro', color: 'text-cyan-400', sfx: 'Brass cup pull + steam' },
                { id: 'SHOT 02', beat: 'Aeration', time: '3.0s', optics: '50mm Whip Pan', color: 'text-purple-400', sfx: 'Liquid rush foley' },
                { id: 'SHOT 03', beat: 'Tasting', time: '2.5s', optics: '35mm Eye-Level', color: 'text-emerald-400', sfx: 'Ambient cafe buzz' },
                { id: 'SHOT 04', beat: 'Punchline', time: '2.5s', optics: '24mm Medium Close', color: 'text-amber-400', sfx: 'Bass drop on cut' },
              ].map((s) => (
                <div key={s.id} className="p-3.5 rounded-2xl bg-black/50 border border-white/10 flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className={`font-bold ${s.color}`}>{s.id}</span>
                    <span className="text-zinc-400">{s.time}</span>
                  </div>
                  <div className="text-sm font-bold text-white">{s.beat} Beat</div>
                  <div className="text-[11px] font-mono text-zinc-400">{s.optics}</div>
                  <div className="text-[10px] font-mono text-zinc-400 truncate bg-black/60 px-2 py-1 rounded border border-white/5">
                    ♫ {s.sfx}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 2: VIDEO ANALYSER */}
      {/* ------------------------------------------------------------- */}
      <section
        id="stage-2"
        className="min-h-screen flex items-center justify-center p-6 sm:p-12"
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center w-full">
          {/* Live UI Mockup Card */}
          <div className="lg:col-span-7 bg-[#0b0e17]/90 glass-hud border border-white/10 rounded-3xl p-6 sm:p-7 shadow-2xl flex flex-col gap-5 text-zinc-200 order-2 lg:order-1">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-xs font-mono text-purple-400 font-bold">MULTIMODAL RETENTION TELEMETRY</span>
              <span className="text-[11px] font-mono text-zinc-400">92.4% Retention Benchmark</span>
            </div>

            {/* Simulated retention curve */}
            <div className="h-40 w-full bg-black/50 rounded-2xl p-4 flex flex-col justify-between border border-white/10 relative overflow-hidden">
              <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400 z-10">
                <span>0.0s (Scroll-Stopper Hook)</span>
                <span>3.0s</span>
                <span>10.0s (Payoff)</span>
              </div>
              <svg className="w-full h-24 overflow-visible" viewBox="0 0 400 80">
                <path
                  d="M 0 10 Q 50 15, 120 28 T 250 32 T 400 45"
                  fill="none"
                  stroke="#a855f7"
                  strokeWidth="3.5"
                />
              </svg>
              <div className="flex items-center gap-2 text-[10px] font-mono text-purple-400 z-10">
                <span className="w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_8px_rgba(168,85,247,0.8)]"></span>
                <span>Visual Disruption Spike at 0.6s</span>
              </div>
            </div>

            {/* Telemetry Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'CUTS / 10S', val: '4.8 cuts', color: 'text-cyan-400' },
                { label: 'HOOK RETENTION', val: '92.4%', color: 'text-emerald-400' },
                { label: 'VOCAL WPM', val: '178 WPM', color: 'text-amber-400' },
                { label: 'AUDIO ENERGY', val: '0.84 RMS', color: 'text-purple-400' },
              ].map((m) => (
                <div key={m.label} className="p-3 rounded-2xl bg-black/40 border border-white/10">
                  <span className="text-[9px] font-mono text-zinc-400 block">{m.label}</span>
                  <span className={`text-base font-bold font-mono ${m.color} block mt-0.5`}>{m.val}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Narrative Card */}
          <div className="lg:col-span-5 flex flex-col gap-4 bg-[#080a10]/80 glass-hud border border-white/10 rounded-3xl p-8 shadow-2xl order-1 lg:order-2">
            <div className="flex items-center justify-between">
              <span className="px-3 py-1 rounded-full text-[10px] font-mono font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30">
                02 // VIDEO ANALYSER
              </span>
              <div className="w-8 h-8 rounded-xl bg-purple-500/15 flex items-center justify-center text-purple-400 border border-purple-500/30">
                <Eye className="w-4 h-4" />
              </div>
            </div>

            <h2 className="text-3xl font-bold text-white tracking-tight">
              Decompile Any Video into Viral Cadence Signals
            </h2>

            <p className="text-xs text-zinc-300 leading-relaxed">
              Extract what makes a Short go viral. Decompile camera motions, cut frequencies, audio spikes, and hook mechanics into quantifiable blueprints.
            </p>

            <div className="space-y-2.5 pt-2 border-t border-white/10 text-xs text-zinc-300">
              <div className="flex items-center gap-2.5">
                <Zap className="w-4 h-4 text-purple-400 shrink-0" />
                <span>Automatic 0–3s scroll-stopper hook formula extraction</span>
              </div>
              <div className="flex items-center gap-2.5">
                <Zap className="w-4 h-4 text-purple-400 shrink-0" />
                <span>Cuts per 10s and vocal cadence (WPM) telemetry</span>
              </div>
              <div className="flex items-center gap-2.5">
                <Zap className="w-4 h-4 text-purple-400 shrink-0" />
                <span>1-click transfer into AI Director to direct in matching cadence</span>
              </div>
            </div>

            <button
              onClick={() => onLaunchStudio('analyser')}
              className="mt-3 w-full py-3 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-500 hover:brightness-110 text-white font-bold text-xs transition-all flex items-center justify-center gap-2 shadow-lg shadow-purple-500/20 active:scale-98 cursor-pointer"
            >
              <span>Launch Video Analyser</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 3: INSPIRATION PLAYBOOK */}
      {/* ------------------------------------------------------------- */}
      <section
        id="stage-3"
        className="min-h-screen flex items-center justify-center p-6 sm:p-12"
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center w-full">
          {/* Narrative Card */}
          <div className="lg:col-span-5 flex flex-col gap-4 bg-[#080a10]/80 glass-hud border border-white/10 rounded-3xl p-8 shadow-2xl">
            <div className="flex items-center justify-between">
              <span className="px-3 py-1 rounded-full text-[10px] font-mono font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                03 // INSPIRATION PLAYBOOK
              </span>
              <div className="w-8 h-8 rounded-xl bg-amber-500/15 flex items-center justify-center text-amber-400 border border-amber-500/30">
                <Sparkles className="w-4 h-4" />
              </div>
            </div>

            <h2 className="text-3xl font-bold text-white tracking-tight">
              Curated Catalog of Proven Outlier Blueprints
            </h2>

            <p className="text-xs text-zinc-300 leading-relaxed">
              Explore decompiled outlier Shorts with verified view metrics. Browse tactical shooting guidelines, categorized topic suggestions, and proven scroll-stopper formulas.
            </p>

            <div className="space-y-2.5 pt-2 border-t border-white/10 text-xs text-zinc-300">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0" />
                <span>Tactical shooting rules & camera choreography</span>
              </div>
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0" />
                <span>Categorized topic concepts & hook recipe formulas</span>
              </div>
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0" />
                <span>Real-time Gemini 3.8 Flash deconstruction on demand</span>
              </div>
            </div>

            <button
              onClick={() => onLaunchStudio('library')}
              className="mt-3 w-full py-3 rounded-xl bg-gradient-to-r from-amber-400 to-orange-400 hover:brightness-110 text-black font-bold text-xs transition-all flex items-center justify-center gap-2 shadow-lg shadow-amber-400/20 active:scale-98 cursor-pointer"
            >
              <span>Explore Inspiration Catalog</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Blueprint Cards */}
          <div className="lg:col-span-7 flex flex-col gap-3">
            {[
              {
                title: 'High-Stakes Surprise Gamble',
                cat: 'ENTERTAINMENT',
                views: '14.2M views',
                duration: '14.0s',
                formula: 'POV Approach Walk + Direct Declaration + High-Impact Prop',
                badgeColor: 'text-purple-300',
              },
              {
                title: 'Tactile Sensory Immersion',
                cat: 'TRAVEL & FOOD',
                views: '8.9M views',
                duration: '11.5s',
                formula: 'Sensory Audio Crunch + Immediate Macro Visual Reveal',
                badgeColor: 'text-amber-300',
              },
              {
                title: 'The Contradiction Confession',
                cat: 'TECH & LIFESTYLE',
                views: '6.4M views',
                duration: '12.0s',
                formula: 'Contrarian Question + 0.6s Visual Whip-Pan Contradiction',
                badgeColor: 'text-cyan-300',
              },
            ].map((b) => (
              <div key={b.title} className="p-5 rounded-2xl border border-white/10 bg-[#080a10]/80 glass-hud shadow-xl flex flex-col gap-2.5">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className={`font-bold ${b.badgeColor}`}>{b.cat}</span>
                  <span className="text-zinc-400">{b.views} • {b.duration}</span>
                </div>
                <h3 className="text-base font-bold text-white">{b.title}</h3>
                <div className="p-2.5 rounded-xl bg-black/40 border border-white/10 text-xs font-mono text-zinc-300">
                  <span className="text-[10px] text-zinc-500 block uppercase font-bold">FORMULA:</span>
                  {b.formula}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 4: AI VIDEO SYNTHESIZER & PERSISTENCE */}
      {/* ------------------------------------------------------------- */}
      <section
        id="stage-4"
        className="min-h-screen flex items-center justify-center p-6 sm:p-12 text-center"
      >
        <div className="w-full max-w-4xl bg-[#080a10]/85 glass-hud border border-white/10 rounded-3xl p-8 sm:p-12 shadow-2xl flex flex-col items-center gap-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            <Video className="w-3.5 h-3.5 text-emerald-400" />
            <span>04 // AI VIDEO SYNTHESIS</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Multi-Shot Video Synthesizer with Character Consistency
          </h2>

          <p className="text-sm text-zinc-300 max-w-2xl leading-relaxed">
            Upload your headshot or character anchor. Locks face, wardrobe, and identity across every shot, assembling a production reference MP4.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full text-left my-2">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <div className="w-8 h-8 rounded-xl bg-emerald-500/15 flex items-center justify-center text-emerald-400 border border-emerald-500/30 mb-2">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <span className="text-xs font-mono font-bold text-white uppercase block">First-Frame Anchor</span>
              <p className="text-xs text-zinc-400 mt-1">Preserves face & wardrobe identity across all cuts</p>
            </div>

            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <div className="w-8 h-8 rounded-xl bg-emerald-500/15 flex items-center justify-center text-emerald-400 border border-emerald-500/30 mb-2">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <span className="text-xs font-mono font-bold text-white uppercase block">Cloud Persistence</span>
              <p className="text-xs text-zinc-400 mt-1">Firestore manifests & GCS bucket media synced</p>
            </div>

            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <div className="w-8 h-8 rounded-xl bg-emerald-500/15 flex items-center justify-center text-emerald-400 border border-emerald-500/30 mb-2">
                <Flame className="w-4 h-4" />
              </div>
              <span className="text-xs font-mono font-bold text-white uppercase block">Creator DNA</span>
              <p className="text-xs text-zinc-400 mt-1">Personalized YouTube Shorts pacing fingerprint</p>
            </div>
          </div>

          <div className="flex items-center gap-3.5 flex-wrap justify-center mt-3">
            <button
              onClick={() => onLaunchStudio('content')}
              className="px-6 py-3.5 rounded-xl bg-white/5 hover:bg-white/10 text-white font-bold text-xs border border-white/10 transition-all flex items-center gap-2 cursor-pointer"
            >
              <span>View Your Content Archive</span>
            </button>

            <button
              onClick={() => onLaunchStudio('director')}
              className="px-7 py-3.5 rounded-xl bg-gradient-to-r from-lime-300 to-emerald-300 text-black font-bold text-xs shadow-xl shadow-lime-300/20 border border-lime-300/40 hover:brightness-110 transition-all flex items-center gap-2 active:scale-95 cursor-pointer"
            >
              <span>Launch Autonomous Studio</span>
              <ArrowRight className="w-4 h-4 text-black" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
