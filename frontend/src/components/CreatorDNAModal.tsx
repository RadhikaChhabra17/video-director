import React, { useState } from 'react';
import {
  X,
  Sparkles,
  Zap,
  Flame,
  Volume2,
  Camera,
  MessageSquareQuote,
  Palette,
  TrendingUp,
  CheckCircle2,
  RefreshCw,
  LogOut,
} from 'lucide-react';
import { YoutubeIcon } from './icons';
import { UserProfile } from '../types/auth';
import { fetchGoogleAuthUrl, sendOAuthCallback, syncCreatorDNA, logoutUser } from '../api/authApi';

interface CreatorDNAModalProps {
  isOpen: boolean;
  onClose: () => void;
  userProfile: UserProfile;
  onUpdateProfile: (profile: UserProfile) => void;
}

export const CreatorDNAModal: React.FC<CreatorDNAModalProps> = ({
  isOpen,
  onClose,
  userProfile,
  onUpdateProfile,
}) => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConnectGoogle = async (useDemo: boolean = false) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      if (useDemo) {
        const profile = await sendOAuthCallback(undefined, true);
        onUpdateProfile(profile);
      } else {
        const authData = await fetchGoogleAuthUrl();
        if (authData.is_configured && authData.auth_url) {
          window.location.href = authData.auth_url;
        } else {
          const profile = await sendOAuthCallback(undefined, true);
          onUpdateProfile(profile);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error connecting account');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSyncDNA = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const updated = await syncCreatorDNA();
      onUpdateProfile(updated);
    } catch (err: any) {
      setErrorMsg(err.message || 'Error syncing DNA');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    setIsLoading(true);
    try {
      await logoutUser();
      onUpdateProfile({ authenticated: false });
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-[#080a10]/95 glass-hud border border-white/10 rounded-3xl w-full max-w-4xl max-h-[90vh] overflow-y-auto custom-scroll flex flex-col shadow-2xl">
        
        {/* Modal Header */}
        <div className="px-4 sm:px-6 py-4 sm:py-5 border-b border-white/10 flex items-center justify-between sticky top-0 bg-[#080a10]/90 backdrop-blur-md z-10">
          <div className="flex items-center gap-2.5 sm:gap-3">
            <div className="w-9 sm:w-10 h-9 sm:h-10 rounded-2xl bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center justify-center shadow-lg shrink-0">
              <YoutubeIcon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-sm sm:text-base font-bold text-white">Google OAuth & Creator DNA</h2>
                {userProfile.authenticated && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    Connected
                  </span>
                )}
              </div>
              <p className="text-xs text-zinc-400 mt-0.5">
                Synchronize your YouTube channel analytics to personalize the AI Director with your signature style.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 text-zinc-400 hover:text-white flex items-center justify-center transition-colors shadow-sm cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 flex flex-col gap-6">
          
          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-200 text-xs font-mono">
              {errorMsg}
            </div>
          )}

          {!userProfile.authenticated ? (
            /* NOT CONNECTED STATE */
            <div className="flex flex-col items-center text-center py-8 px-4 gap-6 max-w-xl mx-auto">
              <div className="w-16 h-16 rounded-3xl bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center justify-center shadow-[0_0_20px_rgba(244,63,94,0.2)]">
                <YoutubeIcon className="w-8 h-8" />
              </div>

              <div>
                <h3 className="text-xl font-bold text-white tracking-tight">Connect Your YouTube Channel</h3>
                <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
                  Authenticate securely via Google OAuth to unlock your channel's real performance data.
                  The AI Director will analyze your highest-retention Shorts to extract your exact pacing,
                  camera preferences, vocal cadence, and audio signatures.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full text-left font-mono text-xs">
                <div className="bg-black/50 border border-white/10 p-3.5 rounded-2xl flex flex-col gap-1 shadow-sm">
                  <span className="text-amber-400 font-bold flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                    Pacing
                  </span>
                  <span className="text-zinc-400 text-[11px]">Calculates cuts/10s baseline</span>
                </div>
                <div className="bg-black/50 border border-white/10 p-3.5 rounded-2xl flex flex-col gap-1 shadow-sm">
                  <span className="text-cyan-400 font-bold flex items-center gap-1.5">
                    <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
                    Audience
                  </span>
                  <span className="text-zinc-400 text-[11px]">Ingests retention curves</span>
                </div>
                <div className="bg-black/50 border border-white/10 p-3.5 rounded-2xl flex flex-col gap-1 shadow-sm">
                  <span className="text-emerald-400 font-bold flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                    DNA Sync
                  </span>
                  <span className="text-zinc-400 text-[11px]">Injects your style in Director</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center gap-3 w-full pt-2">
                <button
                  disabled={isLoading}
                  onClick={() => handleConnectGoogle(false)}
                  className="flex-1 w-full py-3 px-5 rounded-2xl bg-gradient-to-r from-rose-500 to-pink-500 text-white font-bold text-xs hover:brightness-110 transition-all flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(244,63,94,0.3)] cursor-pointer"
                >
                  <YoutubeIcon className="w-4 h-4 text-white shrink-0" />
                  <span>{isLoading ? 'Connecting...' : 'Connect Google & YouTube'}</span>
                </button>

                <button
                  disabled={isLoading}
                  onClick={() => handleConnectGoogle(true)}
                  className="flex-1 w-full py-3 px-5 rounded-2xl bg-white/5 hover:bg-white/10 text-white font-semibold text-xs transition-all flex items-center justify-center gap-2 border border-white/10 shadow-sm cursor-pointer"
                >
                  <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>1-Click Demo Connect (Preview)</span>
                </button>
              </div>
            </div>
          ) : (
            /* CONNECTED CHANNEL & CREATOR DNA STATE */
            <div className="flex flex-col gap-6">
              
              {/* Channel Profile Banner */}
              <div className="bg-black/50 border border-white/10 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
                <div className="flex items-center gap-4">
                  <img
                    src={userProfile.picture || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'}
                    alt={userProfile.name}
                    className="w-14 h-14 rounded-2xl object-cover border border-white/20 shadow-md"
                  />
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-white">{userProfile.channel_title}</h3>
                      <span className="text-xs font-mono text-zinc-400">{userProfile.channel_handle}</span>
                    </div>
                    <span className="text-xs text-zinc-400">{userProfile.email}</span>
                    <div className="flex items-center gap-3 text-xs font-mono text-zinc-400 mt-1">
                      <span>Subscribers: <strong className="text-white">{(userProfile.subscribers_count || 0).toLocaleString()}</strong></span>
                      <span>•</span>
                      <span>Total Views: <strong className="text-white">{(userProfile.total_views || 0).toLocaleString()}</strong></span>
                      <span>•</span>
                      <span>Shorts: <strong className="text-white">{userProfile.shorts_count || 0}</strong></span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    disabled={isLoading}
                    onClick={handleSyncDNA}
                    className="px-3.5 py-2 rounded-xl text-xs font-mono bg-pink-500/15 text-pink-300 border border-pink-500/30 hover:bg-pink-500/25 transition-all flex items-center gap-1.5 font-semibold shadow-sm cursor-pointer"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                    <span>Re-Sync DNA</span>
                  </button>

                  <button
                    disabled={isLoading}
                    onClick={handleLogout}
                    className="px-3 py-2 rounded-xl text-xs font-mono bg-white/5 text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 border border-white/10 transition-colors flex items-center gap-1.5 shadow-sm cursor-pointer"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Disconnect</span>
                  </button>
                </div>
              </div>

              {/* Creator DNA Metrics Cards */}
              {userProfile.creator_dna && (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase font-mono tracking-wider text-pink-400 font-bold flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-pink-400" />
                      Synthesized Creator DNA Fingerprint
                    </span>
                    <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      Active in AI Director Prompts
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    <div className="bg-black/50 border border-white/10 rounded-2xl p-4 flex flex-col gap-1.5 shadow-sm">
                      <div className="flex items-center gap-2 text-zinc-400 text-xs font-mono">
                        <Zap className="w-3.5 h-3.5 text-amber-400" />
                        <span>PACING CADENCE</span>
                      </div>
                      <span className="text-lg font-bold text-white font-mono">
                        {userProfile.creator_dna.pacing_baseline_cuts_per_10s} cuts / 10s
                      </span>
                      <p className="text-[11px] text-zinc-400">Baseline cut frequency calibrated to your viral shorts.</p>
                    </div>

                    <div className="bg-black/50 border border-white/10 rounded-2xl p-4 flex flex-col gap-1.5 shadow-sm">
                      <div className="flex items-center gap-2 text-zinc-400 text-xs font-mono">
                        <Camera className="w-3.5 h-3.5 text-cyan-400" />
                        <span>SIGNATURE FRAMING</span>
                      </div>
                      <span className="text-xs font-bold text-zinc-200">
                        {userProfile.creator_dna.signature_framing}
                      </span>
                      <p className="text-[11px] text-zinc-400">Default optical choices for shot descriptions.</p>
                    </div>

                    <div className="bg-black/50 border border-white/10 rounded-2xl p-4 flex flex-col gap-1.5 shadow-sm">
                      <div className="flex items-center gap-2 text-zinc-400 text-xs font-mono">
                        <MessageSquareQuote className="w-3.5 h-3.5 text-emerald-400" />
                        <span>VOCAL CADENCE</span>
                      </div>
                      <span className="text-lg font-bold text-white font-mono">
                        {userProfile.creator_dna.vocal_cadence_wpm} WPM
                      </span>
                      <p className="text-[11px] text-zinc-400">Target words-per-minute for dialogue timing.</p>
                    </div>

                    <div className="bg-black/50 border border-white/10 rounded-2xl p-4 flex flex-col gap-1.5 shadow-sm">
                      <div className="flex items-center gap-2 text-zinc-400 text-xs font-mono">
                        <Volume2 className="w-3.5 h-3.5 text-purple-400" />
                        <span>AUDIO ENERGY PROFILE</span>
                      </div>
                      <span className="text-xs font-bold text-zinc-200">
                        {userProfile.creator_dna.audio_energy_profile}
                      </span>
                      <p className="text-[11px] text-zinc-400">Sound design & transition effects automatically applied.</p>
                    </div>

                    <div className="bg-black/50 border border-white/10 rounded-2xl p-4 flex flex-col gap-1.5 shadow-sm">
                      <div className="flex items-center gap-2 text-zinc-400 text-xs font-mono">
                        <Flame className="w-3.5 h-3.5 text-rose-400" />
                        <span>HOOK TYPE PREFERENCE</span>
                      </div>
                      <span className="text-xs font-bold text-zinc-200">
                        {userProfile.creator_dna.signature_hook_type}
                      </span>
                      <p className="text-[11px] text-zinc-400">Opening 0-2s beat structure matching your top retention.</p>
                    </div>

                    <div className="bg-black/50 border border-white/10 rounded-2xl p-4 flex flex-col gap-1.5 shadow-sm">
                      <div className="flex items-center gap-2 text-zinc-400 text-xs font-mono">
                        <Palette className="w-3.5 h-3.5 text-teal-400" />
                        <span>COLOR & MOOD</span>
                      </div>
                      <span className="text-xs font-bold text-zinc-200">
                        {userProfile.creator_dna.color_palette}
                      </span>
                      <p className="text-[11px] text-zinc-400">Visual atmosphere default: {userProfile.creator_dna.retention_benchmark}% benchmark.</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Top Performing Shorts Ingested */}
              {userProfile.top_shorts && userProfile.top_shorts.length > 0 && (
                <div className="flex flex-col gap-3">
                  <span className="text-xs uppercase font-mono tracking-wider text-zinc-400 font-bold">
                    Top Ingested YouTube Shorts ({userProfile.top_shorts.length} Active Benchmarks)
                  </span>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {userProfile.top_shorts.map((short) => (
                      <div
                        key={short.video_id}
                        className="bg-black/50 border border-white/10 rounded-2xl p-4 flex flex-col justify-between gap-3 shadow-sm"
                      >
                        <div className="flex flex-col gap-1.5">
                          <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400">
                            <span>{short.published_date}</span>
                            <span>{short.duration_sec}s</span>
                          </div>
                          <h4 className="text-xs font-bold text-white line-clamp-2">{short.title}</h4>
                        </div>

                        <div className="pt-2 border-t border-white/10 flex flex-col gap-1 text-[11px] font-mono">
                          <div className="flex items-center justify-between">
                            <span className="text-zinc-500 text-[10px]">VIEWS</span>
                            <span className="text-zinc-200 font-bold">{short.views.toLocaleString()}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-zinc-500 text-[10px]">RETENTION</span>
                            <span className="text-emerald-400 font-bold">{short.retention_rate}%</span>
                          </div>
                          <div className="mt-1 text-[10px] text-amber-300 bg-amber-950/30 p-1.5 rounded-lg border border-amber-500/30">
                            Hook: {short.top_hook}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}

        </div>

      </div>
    </div>
  );
};
