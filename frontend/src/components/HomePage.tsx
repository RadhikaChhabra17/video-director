import React, { useState, useEffect, useRef } from 'react';
import { UserProfile } from '../types/auth';
import { SpotlightBeam } from './SpotlightBeam';

interface HomePageProps {
  onNavigate: (module: 'director' | 'analyser' | 'content' | 'library') => void;
  manifestsCount?: number;
  corpusCount?: number;
  patternsCount?: number;
  userProfile?: UserProfile;
  onOpenGoogleAuth?: () => void;
  onFocalChange?: (index: number) => void;
}

interface FocalStop {
  mm: string;
  name: string;
  title: string;
  description: string;
  module: 'director' | 'analyser' | 'content' | 'library';
  color: string;
  borderActive: string;
  bgActive: string;
  glow: string;
  rgb: string;
  colorHex: string;
}

const FOCAL_STOPS: FocalStop[] = [
  {
    mm: '24mm',
    name: 'DIRECTOR MODE',
    title: 'AI Director',
    description: 'Shot planning & storytelling',
    module: 'director',
    color: 'text-cyan-400',
    borderActive: 'border-cyan-400/50',
    bgActive: 'bg-cyan-500/10',
    glow: 'shadow-[0_0_25px_rgba(34,211,238,0.35)]',
    rgb: '0, 240, 255',
    colorHex: '#00f0ff',
  },
  {
    mm: '35mm',
    name: 'ANALYZER MODE',
    title: 'Video Analyzer',
    description: 'Patterns, pacing & hooks',
    module: 'analyser',
    color: 'text-purple-400',
    borderActive: 'border-purple-400/50',
    bgActive: 'bg-purple-500/10',
    glow: 'shadow-[0_0_25px_rgba(168,85,247,0.35)]',
    rgb: '168, 85, 247',
    colorHex: '#a855f7',
  },
  {
    mm: '50mm',
    name: 'CREATOR DNA',
    title: 'Creator DNA',
    description: 'Your style & content',
    module: 'content',
    color: 'text-pink-400',
    borderActive: 'border-pink-400/50',
    bgActive: 'bg-pink-500/10',
    glow: 'shadow-[0_0_25px_rgba(244,63,94,0.35)]',
    rgb: '244, 63, 94',
    colorHex: '#f43f5e',
  },
  {
    mm: '85mm',
    name: 'INSPIRATION MODE',
    title: 'Inspiration',
    description: 'Viral patterns & references',
    module: 'library',
    color: 'text-amber-400',
    borderActive: 'border-amber-400/50',
    bgActive: 'bg-amber-500/10',
    glow: 'shadow-[0_0_25px_rgba(245,158,11,0.35)]',
    rgb: '245, 158, 11',
    colorHex: '#f59e0b',
  },
];

export const HomePage: React.FC<HomePageProps> = ({
  onNavigate,
  onFocalChange,
}) => {
  const [activeFocalIndex, setActiveFocalIndex] = useState<number>(0);
  const pageRef = useRef<HTMLDivElement | null>(null);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Live ticking timecode for red dot REC {CURR_TIME}
  const [currentTime, setCurrentTime] = useState<string>(() => {
    const now = new Date();
    return now.toTimeString().split(' ')[0];
  });

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setCurrentTime(now.toTimeString().split(' ')[0]);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleSelectFocal = (index: number) => {
    setActiveFocalIndex(index);
    onFocalChange?.(index);
  };

  const handleEnterStudio = () => {
    const selectedStop = FOCAL_STOPS[activeFocalIndex];
    onNavigate(selectedStop.module);
  };

  const currentStop = FOCAL_STOPS[activeFocalIndex];

  return (
    <div
      ref={pageRef}
      className="relative flex-1 w-full h-full min-h-screen flex flex-col justify-between p-4 sm:p-6 md:p-10 pointer-events-none select-none z-20 overflow-hidden"
    >
      {/* Single Overhead Stage Spotlight from Top of the Page */}
      <SpotlightBeam
        pageRef={pageRef}
        buttonRefs={buttonRefs}
        activeFocalIndex={activeFocalIndex}
        colorRgb={currentStop.rgb}
        colorHex={currentStop.colorHex}
      />
      
      {/* 1. Header Bar: Red Dot REC {CURR_TIME} */}
      <div className="w-full flex items-center justify-between pointer-events-auto pt-1 sm:pt-0 relative z-20">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 sm:gap-2.5 px-3 sm:px-3.5 py-1.5 bg-black/60 border border-white/10 rounded-full backdrop-blur-md shadow-lg">
            <span className="w-2 sm:w-2.5 h-2 sm:h-2.5 rounded-full bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.9)]"></span>
            <span className="font-mono text-[11px] sm:text-xs text-red-400 font-bold tracking-wider">
              REC {currentTime}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Optical Telemetry Data */}
      <div className="mt-6 sm:mt-10 md:mt-12 max-w-2xl pointer-events-auto relative z-20">
        <h1 className="text-2xl xs:text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-white drop-shadow-md whitespace-nowrap">
          Your stories, reimagined.
        </h1>
        <p className="text-zinc-400 text-xs sm:text-sm mt-2 sm:mt-2.5 leading-relaxed max-w-lg">
          Make something worth watching. Explore the frames, then step into your creative workspace.
        </p>
      </div>

      {/* 3. Bottom Focal Rings Selector Bar */}
      <div className="w-full flex flex-col items-center pointer-events-auto mb-2 sm:mb-4 mt-auto relative z-20">
        <div className="w-full max-w-3xl glass-hud rounded-2xl p-3.5 sm:p-5 flex flex-col gap-3 border border-white/10 shadow-2xl backdrop-blur-2xl relative">
          <div className="flex justify-between items-center font-mono text-zinc-400 px-1 relative z-10">
            <span className="flex items-center gap-2">
              <span className="text-[11px] sm:text-xs font-semibold tracking-wider text-zinc-400">NOW SHOWING:</span>
              <span className={`font-extrabold tracking-wider text-xs sm:text-sm ${currentStop.color} drop-shadow-sm`}>
                {currentStop.name}
              </span>
            </span>
          </div>

          {/* 4 Mechanical Focal Ring Selectors */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-2.5 relative z-10">
            {FOCAL_STOPS.map((stop, idx) => {
              const isSelected = activeFocalIndex === idx;
              return (
                <button
                  key={stop.mm}
                  ref={(el) => (buttonRefs.current[idx] = el)}
                  onClick={() => handleSelectFocal(idx)}
                  onDoubleClick={() => onNavigate(stop.module)}
                  className={`relative p-3 rounded-xl text-left transition-all duration-300 cursor-pointer ${
                    isSelected
                      ? `${stop.borderActive} ${stop.bgActive} ${stop.glow} scale-[1.02] border-t-2 border-t-white/80 shadow-[inset_0_4px_16px_rgba(255,255,255,0.22)]`
                      : 'border border-white/5 bg-white/5 hover:border-white/20 hover:bg-white/10'
                  }`}
                  title={`Double click to enter ${stop.title}`}
                >
                  <div className={`font-mono text-[10px] sm:text-[11px] font-bold ${stop.color}`}>
                    {stop.mm}
                  </div>
                  <div className="text-xs sm:text-sm font-bold text-white mt-0.5 truncate">
                    {stop.title}
                  </div>
                  <div className="text-[10px] sm:text-[11px] text-zinc-400 truncate mt-0.5">
                    {stop.description}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Push In Action Button */}
          <button
            onClick={handleEnterStudio}
            className="w-full py-3 sm:py-3.5 bg-gradient-to-r from-lime-300 to-emerald-300 hover:brightness-110 text-black font-bold text-xs rounded-xl tracking-wider transition shadow-lg shadow-lime-300/20 active:scale-95 text-center mt-0.5 cursor-pointer flex items-center justify-center gap-2 font-mono"
          >
            <span>ENTER THE CREATIVE STUDIO [ ↗ ]</span>
          </button>
        </div>
      </div>

    </div>
  );
};
