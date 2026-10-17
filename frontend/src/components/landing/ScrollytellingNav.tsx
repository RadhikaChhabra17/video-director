import React from 'react';
import { Film, Eye, Sparkles, Video, ArrowRight, Sparkle } from 'lucide-react';

interface ScrollytellingNavProps {
  activeStage: number; // 0: Hero, 1: Director, 2: Analyser, 3: Inspiration, 4: Video Synthesis
  onJumpToStage: (stage: number) => void;
  onLaunchStudio: (module: 'director' | 'analyser' | 'content' | 'library') => void;
}

export const ScrollytellingNav: React.FC<ScrollytellingNavProps> = ({
  activeStage,
  onJumpToStage,
  onLaunchStudio,
}) => {
  const navItems = [
    {
      stage: 1,
      module: 'director' as const,
      label: 'AI Director',
      icon: Film,
      badge: '01',
      accent: 'text-cyan-400',
      activeBorder: 'border-cyan-400/50 bg-cyan-500/15 text-cyan-300 font-bold shadow-[0_0_12px_rgba(0,240,255,0.2)]',
    },
    {
      stage: 2,
      module: 'analyser' as const,
      label: 'Video Analyser',
      icon: Eye,
      badge: '02',
      accent: 'text-purple-400',
      activeBorder: 'border-purple-400/50 bg-purple-500/15 text-purple-300 font-bold shadow-[0_0_12px_rgba(168,85,247,0.2)]',
    },
    {
      stage: 3,
      module: 'library' as const,
      label: 'Inspiration',
      icon: Sparkles,
      badge: '03',
      accent: 'text-amber-400',
      activeBorder: 'border-amber-400/50 bg-amber-500/15 text-amber-300 font-bold shadow-[0_0_12px_rgba(245,158,11,0.2)]',
    },
    {
      stage: 4,
      module: 'content' as const,
      label: 'Video Synthesizer',
      icon: Video,
      badge: '04',
      accent: 'text-emerald-400',
      activeBorder: 'border-emerald-400/50 bg-emerald-500/15 text-emerald-300 font-bold shadow-[0_0_12px_rgba(16,185,129,0.2)]',
    },
  ];

  return (
    <header className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[95%] max-w-5xl transition-all">
      <div className="bg-[#080a10]/80 glass-hud border border-white/10 shadow-2xl rounded-2xl px-4 py-2.5 flex items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => onJumpToStage(0)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-mono font-semibold bg-white/5 text-white border border-white/10 hover:bg-white/10 hover:border-cyan-400/40 transition-all cursor-pointer shadow-sm"
            title="Return to top"
          >
            <Sparkle className="w-3.5 h-3.5 text-cyan-400" />
            <span className="font-bold tracking-wide">Creative Room</span>
          </button>

          <span className="h-4 w-px bg-white/10 hidden sm:block"></span>

          <span className="text-[11px] font-mono uppercase tracking-widest text-zinc-400 font-bold hidden md:inline">
            Autonomous Shorts Studio
          </span>
        </div>

        {/* Center Chapter Nav Items */}
        <nav className="flex items-center gap-1 sm:gap-2">
          {navItems.map((item) => {
            const isActive = activeStage === item.stage;
            const Icon = item.icon;
            return (
              <button
                key={item.stage}
                onClick={() => onJumpToStage(item.stage)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs transition-all border cursor-pointer ${
                  isActive
                    ? item.activeBorder
                    : 'border-transparent text-zinc-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <span className="text-[10px] font-mono opacity-60">
                  {item.badge}
                </span>
                <Icon className={`w-3.5 h-3.5 ${isActive ? item.accent : 'text-zinc-500'}`} />
                <span className="hidden lg:inline">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right Studio Direct Launch Button */}
        <div>
          <button
            onClick={() => {
              const current = navItems.find((i) => i.stage === activeStage);
              onLaunchStudio(current ? current.module : 'director');
            }}
            className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-lime-300 to-emerald-300 text-black border border-lime-300/40 hover:brightness-110 active:scale-95 transition-all shadow-[0_0_15px_rgba(190,242,100,0.3)] flex items-center gap-1.5 cursor-pointer"
          >
            <span className="hidden sm:inline">Launch Studio</span>
            <span className="sm:hidden">Launch</span>
            <ArrowRight className="w-3.5 h-3.5 text-black" />
          </button>
        </div>
      </div>
    </header>
  );
};
