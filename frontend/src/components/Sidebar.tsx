import React from 'react';
import {
  Film,
  Home,
  Eye,
  Layers,
  Sparkles,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { UserProfile } from '../types/auth';

interface SidebarProps {
  currentModule: 'home' | 'director' | 'analyser' | 'content' | 'library';
  onNavigate: (module: 'home' | 'director' | 'analyser' | 'content' | 'library') => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  userProfile?: UserProfile;
  onOpenGoogleAuth?: () => void;
  counts?: {
    manifests: number;
    corpus: number;
    patterns: number;
  };
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentModule,
  onNavigate,
  isCollapsed,
  onToggleCollapse,
  userProfile,
  onOpenGoogleAuth,
}) => {
  const workspaceItems = [
    {
      id: 'home' as const,
      label: 'Home',
      icon: Home,
      accent: 'text-zinc-200',
      activeBg: 'bg-white/10 text-white border border-white/20 font-semibold shadow-sm',
    },
    {
      id: 'director' as const,
      label: 'AI Director',
      icon: Film,
      accent: 'text-cyan-400',
      activeBg: 'bg-cyan-500/15 text-cyan-300 border border-cyan-400/40 font-semibold shadow-[0_0_15px_rgba(0,240,255,0.15)]',
    },
    {
      id: 'analyser' as const,
      label: 'Video Analyser',
      icon: Eye,
      accent: 'text-purple-400',
      activeBg: 'bg-purple-500/15 text-purple-300 border border-purple-400/40 font-semibold shadow-[0_0_15px_rgba(168,85,247,0.15)]',
    },
  ];

  const assetItems = [
    {
      id: 'content' as const,
      label: 'Your Content',
      icon: Layers,
      accent: 'text-pink-400',
      activeBg: 'bg-pink-500/15 text-pink-300 border border-pink-400/40 font-semibold shadow-[0_0_15px_rgba(244,63,94,0.15)]',
    },
    {
      id: 'library' as const,
      label: 'Inspiration',
      icon: Sparkles,
      accent: 'text-amber-400',
      activeBg: 'bg-amber-500/15 text-amber-300 border border-amber-400/40 font-semibold shadow-[0_0_15px_rgba(245,158,11,0.15)]',
    },
  ];

  return (
    <aside
      className={`${
        isCollapsed ? 'w-16' : 'w-60'
      } bg-[#06080d]/90 border-r border-white/10 flex flex-col justify-between shrink-0 select-none z-30 transition-all duration-200 ease-in-out backdrop-blur-xl text-white`}
    >
      <div className="flex flex-col">
        
        {/* Brand Header */}
        <div className="h-14 px-4 border-b border-white/10 flex items-center justify-between">
          <div
            onClick={() => onNavigate('home')}
            className="flex items-center gap-2.5 cursor-pointer group"
          >
            <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 shrink-0 group-hover:scale-125 transition-transform shadow-[0_0_8px_#00f0ff]"></div>
            {!isCollapsed && (
              <span className="text-xs uppercase font-mono tracking-widest text-zinc-200 font-bold group-hover:text-cyan-400 transition-colors">
                FRAME STUDIO
              </span>
            )}
          </div>

          {!isCollapsed && (
            <button
              onClick={onToggleCollapse}
              className="text-zinc-500 hover:text-zinc-200 transition-colors cursor-pointer"
              title="Collapse sidebar"
            >
              <PanelLeftClose className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <div className="p-2.5 flex flex-col gap-5">
          
          {/* Group 1: Workspace */}
          <div>
            {!isCollapsed && (
              <span className="px-2.5 text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-semibold block mb-1">
                Workspace
              </span>
            )}
            <nav className="space-y-1">
              {workspaceItems.map((item) => {
                const isActive = currentModule === item.id;
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    title={isCollapsed ? item.label : undefined}
                    className={`w-full rounded-xl text-xs font-mono flex items-center transition-all cursor-pointer ${
                      isCollapsed ? 'justify-center p-2.5' : 'justify-between px-3 py-2'
                    } ${
                      isActive
                        ? item.activeBg
                        : 'text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={`w-4 h-4 shrink-0 ${isActive ? item.accent : 'text-zinc-500'}`} />
                      {!isCollapsed && <span>{item.label}</span>}
                    </div>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Group 2: Assets & Intelligence */}
          <div>
            {!isCollapsed && (
              <span className="px-2.5 text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-semibold block mb-1">
                Creative Intelligence
              </span>
            )}
            <nav className="space-y-1">
              {assetItems.map((item) => {
                const isActive = currentModule === item.id;
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    title={isCollapsed ? item.label : undefined}
                    className={`w-full rounded-xl text-xs font-mono flex items-center transition-all cursor-pointer ${
                      isCollapsed ? 'justify-center p-2.5' : 'justify-between px-3 py-2'
                    } ${
                      isActive
                        ? item.activeBg
                        : 'text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={`w-4 h-4 shrink-0 ${isActive ? item.accent : 'text-zinc-500'}`} />
                      {!isCollapsed && <span>{item.label}</span>}
                    </div>
                  </button>
                );
              })}
            </nav>
          </div>

        </div>
      </div>

      {/* FOOTER: Google / YouTube OAuth & Collapse Button */}
      <div className="p-2.5 border-t border-white/10 flex flex-col gap-2">
        {onOpenGoogleAuth && userProfile?.authenticated && (
          <div>
            <button
              onClick={onOpenGoogleAuth}
              title={userProfile.channel_title}
              className={`w-full rounded-xl bg-black/60 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-all flex items-center shadow-sm cursor-pointer ${
                isCollapsed ? 'justify-center p-2' : 'p-2.5 gap-2.5'
              }`}
            >
              <img
                src={userProfile.picture || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'}
                alt={userProfile.name}
                className="w-7 h-7 rounded-lg object-cover border border-white/15 shrink-0"
              />
              {!isCollapsed && (
                <div className="truncate flex-1 text-left">
                  <span className="text-xs font-bold text-zinc-200 truncate block">
                    {userProfile.channel_title}
                  </span>
                  <span className="text-[9px] font-mono text-emerald-400 flex items-center gap-1 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    DNA Synced
                  </span>
                </div>
              )}
            </button>
          </div>
        )}

        {/* Mini expand button if collapsed */}
        {isCollapsed && (
          <button
            onClick={onToggleCollapse}
            className="w-full py-1.5 flex items-center justify-center text-zinc-500 hover:text-zinc-200 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
            title="Expand sidebar"
          >
            <PanelLeftOpen className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

    </aside>
  );
};
