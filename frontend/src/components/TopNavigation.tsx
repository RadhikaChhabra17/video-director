import React from 'react';
import {
  ArrowLeft,
  PanelLeftClose,
  PanelLeftOpen,
  ChevronRight,
  Home,
  Film,
  Eye,
  Layers,
  Copy,
  Check,
  Sparkles,
  Play,
} from 'lucide-react';
import { DirectorResponseManifest } from '../types/director';
import { UserProfile } from '../types/auth';

interface TopNavigationProps {
  currentModule: 'home' | 'director' | 'analyser' | 'content' | 'library';
  onNavigate: (module: 'home' | 'director' | 'analyser' | 'content' | 'library') => void;
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  currentManifest: DirectorResponseManifest | null;
  canGoBack?: boolean;
  onGoBack?: () => void;
  onCopyJson?: () => void;
  copyStatus?: string | null;
  onOpenReferenceVideo?: () => void;
  userProfile?: UserProfile;
  onOpenGoogleAuth?: () => void;
}

export const TopNavigation: React.FC<TopNavigationProps> = ({
  currentModule,
  onNavigate,
  isSidebarCollapsed,
  onToggleSidebar,
  currentManifest,
  canGoBack,
  onGoBack,
  onCopyJson,
  copyStatus,
  onOpenReferenceVideo,
  userProfile,
  onOpenGoogleAuth,
}) => {

  const getModuleLabel = () => {
    switch (currentModule) {
      case 'home':
        return 'Overview';
      case 'director':
        return 'AI Director';
      case 'analyser':
        return 'Video Analyser';
      case 'content':
        return 'Your Content';
      case 'library':
        return 'Inspiration';
    }
  };

  const navItems = [
    { id: 'home' as const, label: 'Home', icon: Home, activeColor: 'text-white border-white/30 bg-white/10' },
    { id: 'director' as const, label: 'AI Director', icon: Film, activeColor: 'text-cyan-300 border-cyan-400/40 bg-cyan-500/15 shadow-[0_0_12px_rgba(0,240,255,0.15)]' },
    { id: 'analyser' as const, label: 'Video Analyser', icon: Eye, activeColor: 'text-purple-300 border-purple-400/40 bg-purple-500/15 shadow-[0_0_12px_rgba(168,85,247,0.15)]' },
    { id: 'content' as const, label: 'Your Content', icon: Layers, activeColor: 'text-pink-300 border-pink-400/40 bg-pink-500/15 shadow-[0_0_12px_rgba(244,63,94,0.15)]' },
    { id: 'library' as const, label: 'Inspiration', icon: Sparkles, activeColor: 'text-amber-300 border-amber-400/40 bg-amber-500/15 shadow-[0_0_12px_rgba(245,158,11,0.15)]' },
  ];

  return (
    <header className="h-14 border-b border-white/10 px-4 lg:px-6 flex items-center justify-between bg-[#080a10]/80 shrink-0 z-40 select-none backdrop-blur-xl text-white">
      
      {/* LEFT: Sidebar Toggle & Interactive Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          title={isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          className="w-8 h-8 rounded-lg bg-black/60 border border-white/10 text-zinc-300 hover:text-white hover:border-white/20 hover:bg-white/5 flex items-center justify-center transition-all shrink-0 shadow-sm active:scale-95 cursor-pointer"
        >
          {isSidebarCollapsed ? (
            <PanelLeftOpen className="w-4 h-4" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
          )}
        </button>

        <div className="h-4 w-px bg-white/15 hidden sm:block"></div>

        {/* Back Button */}
        {onGoBack && (
          <button
            onClick={onGoBack}
            disabled={!canGoBack}
            title={canGoBack ? 'Go back' : 'No previous history'}
            className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
              canGoBack
                ? 'bg-black/60 hover:bg-white/10 text-zinc-200 hover:text-white hover:scale-105 active:scale-95 border border-white/10 shadow-sm cursor-pointer'
                : 'text-zinc-600 cursor-not-allowed opacity-30 border border-transparent'
            }`}
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
        )}

        {/* Breadcrumb Trail */}
        <nav className="flex items-center gap-2 text-xs font-mono">
          <button
            onClick={() => onNavigate('home')}
            className="text-zinc-400 hover:text-white transition-colors font-medium flex items-center gap-1.5 cursor-pointer"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
            FRAME
          </button>
          
          <ChevronRight className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
          
          <span
            className={`font-semibold tracking-wider ${
              currentModule === 'director'
                ? 'text-cyan-400'
                : currentModule === 'analyser'
                ? 'text-purple-400'
                : currentModule === 'content'
                ? 'text-pink-400'
                : currentModule === 'library'
                ? 'text-amber-400'
                : 'text-white'
            }`}
          >
            {getModuleLabel()}
          </span>
        </nav>
      </div>

      {/* CENTER: Quick Workspace Mode Tabs */}
      <div className="hidden md:flex items-center bg-black/60 p-1 rounded-xl border border-white/10 gap-1 shadow-inner">
        {navItems.map((item) => {
          const isActive = currentModule === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-1.5 cursor-pointer ${
                isActive
                  ? `border font-semibold ${item.activeColor}`
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border border-transparent'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* RIGHT: Actions, YouTube DNA Pill, Director Controls */}
      <div className="flex items-center gap-2.5">
        
        {/* If in Director Mode: Manifest Actions (Copy as JSON & Create Reference Video) */}
        {currentModule === 'director' && currentManifest && (
          <div className="flex items-center gap-2">
            {onOpenReferenceVideo && (
              <button
                onClick={onOpenReferenceVideo}
                className="px-3.5 py-1.5 rounded-xl text-xs font-bold tracking-wider font-mono transition-all flex items-center gap-1.5 shadow-lg shadow-lime-300/15 active:scale-95 bg-gradient-to-r from-lime-300 to-emerald-300 hover:brightness-110 text-black cursor-pointer"
                title={
                  currentManifest.total_target_duration_sec > 10.0
                    ? `Duration (${currentManifest.total_target_duration_sec.toFixed(1)}s) exceeds 10s limit`
                    : 'Create reference video using Gemini Omni 1.1 Flash'
                }
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span className="hidden sm:inline">Reference Video</span>
                <span className="sm:hidden">Video</span>
              </button>
            )}

            {onCopyJson && (
              <button
                onClick={onCopyJson}
                className={`px-3 py-1.5 rounded-xl text-xs font-mono transition-all flex items-center gap-1.5 shadow-sm active:scale-95 border cursor-pointer ${
                  copyStatus
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/40'
                    : 'bg-black/60 hover:bg-white/10 text-zinc-200 border-white/10 hover:border-white/20'
                }`}
                title="Copy clean production manifest JSON to clipboard"
              >
                {copyStatus ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-300" />
                    <span className="font-semibold text-emerald-300">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-zinc-400" />
                    <span>Copy JSON</span>
                  </>
                )}
              </button>
            )}
          </div>
        )}

        {/* YouTube / Google OAuth Pill */}
        {onOpenGoogleAuth && userProfile?.authenticated && (
          <button
            onClick={onOpenGoogleAuth}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-black/60 border border-white/10 hover:border-white/25 text-xs font-mono transition-all group shadow-sm text-zinc-200 cursor-pointer"
          >
            <img
              src={userProfile.picture || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'}
              alt={userProfile.name}
              className="w-5 h-5 rounded-full object-cover border border-white/15 shrink-0"
            />
            <span className="text-zinc-200 font-semibold max-w-[100px] truncate hidden sm:inline">
              {userProfile.channel_handle || userProfile.channel_title}
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
          </button>
        )}


      </div>
    </header>
  );
};

