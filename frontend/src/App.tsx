import { useState, useEffect, useRef } from 'react';
import {
  DirectorResponseManifest,
  DirectorShotPlan,
  ManifestSummary,
  DirectRequest,
} from './types/director';
import {
  fetchManifests,
  fetchManifest,
  saveManifest,
  directVideo,
  cancelDirect,
  refineShot,
  fetchPatterns,
  fetchAnalyses,
} from './api/directorApi';
import { HomePage } from './components/HomePage';
import { VideoAnalyser } from './components/VideoAnalyser';
import { YourContent } from './components/YourContent';
import { ContentLibrary } from './components/ContentLibrary';
import { PromptPanel } from './components/PromptPanel';
import { ShotCard } from './components/ShotCard';
import { CreatorDNAModal } from './components/CreatorDNAModal';
import { ReferenceVideoModal } from './components/ReferenceVideoModal';
import { ThreeCanvas } from './components/ThreeCanvas';
import { UserProfile } from './types/auth';
import { fetchUserProfile, sendOAuthCallback } from './api/authApi';
import { Clock, AlertCircle, Plus, Sparkles, Save, Check, RotateCcw, XCircle, Play, Copy } from 'lucide-react';
import { INSPIRATION_SHORTS } from './data/inspirationShorts';

export function App() {
  const [currentModule, setCurrentModule] = useState<'home' | 'director' | 'analyser' | 'content' | 'library'>('home');
  const [homeFocalIndex, setHomeFocalIndex] = useState<number>(0);
  const [navHistory, setNavHistory] = useState<('home' | 'director' | 'analyser' | 'content' | 'library')[]>(['home']);
  const [manifests, setManifests] = useState<ManifestSummary[]>([]);
  const [currentManifest, setCurrentManifest] = useState<DirectorResponseManifest | null>(null);
  const [patterns, setPatterns] = useState<any[]>(INSPIRATION_SHORTS);
  const [analyses, setAnalyses] = useState<any[]>([]);

  const [userProfile, setUserProfile] = useState<UserProfile>({ authenticated: false });
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [isRefVideoModalOpen, setIsRefVideoModalOpen] = useState<boolean>(false);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isDirecting, setIsDirecting] = useState<boolean>(false);
  const [refiningShotId, setRefiningShotId] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const directAbortControllerRef = useRef<AbortController | null>(null);
  const prevModuleRef = useRef(currentModule);

  const [activeBrief, setActiveBrief] = useState<{
    script: string;
    duration: number;
    category?: string;
    referenceTitle?: string;
    referenceVideoId?: string;
    activeDirectionTag?: string;
  } | null>({
    script: 'First time trying authentic South Indian filter coffee pulled between brass cups in Bangalore cafe. Pure adrenaline, steam, and strong chicory.',
    duration: 8.0,
  });

  // Refresh AI Director state and abort any active running process
  const resetDirectorState = () => {
    if (directAbortControllerRef.current) {
      directAbortControllerRef.current.abort();
      directAbortControllerRef.current = null;
    }
    cancelDirect().catch(() => {});
    setIsDirecting(false);
    setCurrentManifest(null);
    setActiveBrief({
      script: 'First time trying authentic South Indian filter coffee pulled between brass cups in Bangalore cafe. Pure adrenaline, steam, and strong chicory.',
      duration: 8.0,
    });
    setIsRefVideoModalOpen(false);
    setErrorMsg(null);
  };

  // Automatically refresh AI Director state when leaving the director view
  useEffect(() => {
    if (prevModuleRef.current === 'director' && currentModule !== 'director') {
      resetDirectorState();
    }
    prevModuleRef.current = currentModule;
  }, [currentModule]);

  // Synchronize browser history (popstate / pushState) so browser Back & Forward preserve app navigation
  useEffect(() => {
    if (!window.history.state || !window.history.state.module) {
      window.history.replaceState({ module: currentModule }, '', window.location.pathname);
    }

    const handlePopState = (event: PopStateEvent) => {
      const targetModule = event.state?.module || 'home';
      setCurrentModule(targetModule);
      setNavHistory((prev) => {
        if (prev.length > 1 && prev[prev.length - 2] === targetModule) {
          const next = [...prev];
          next.pop();
          return next;
        }
        if (prev[prev.length - 1] === targetModule) {
          return prev;
        }
        return [...prev, targetModule];
      });
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleNavigate = (module: 'home' | 'director' | 'analyser' | 'content' | 'library') => {
    if (module === currentModule) return;
    setNavHistory((prev) => [...prev, module]);
    setCurrentModule(module);
    window.history.pushState({ module }, '', window.location.pathname);
  };

  const handleGoBack = () => {
    if (navHistory.length > 1) {
      const nextHistory = [...navHistory];
      nextHistory.pop();
      const prevModule = nextHistory[nextHistory.length - 1];
      setNavHistory(nextHistory);
      setCurrentModule(prevModule);
      window.history.pushState({ module: prevModule }, '', window.location.pathname);
    } else if (currentModule !== 'home') {
      setNavHistory(['home']);
      setCurrentModule('home');
      window.history.pushState({ module: 'home' }, '', window.location.pathname);
    }
  };

  useEffect(() => {
    loadInitialData();
    checkAuthSession();
  }, []);

  const checkAuthSession = async () => {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const demo = urlParams.get('demo');
      if (code || demo === 'true') {
        const profile = await sendOAuthCallback(code || undefined, demo === 'true');
        setUserProfile(profile);
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
      }

      const profile = await fetchUserProfile();
      setUserProfile(profile);
    } catch {
      // ignore unauthenticated session
    }
  };

  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      const manifestsPromise = fetchManifests().catch(() => []);
      const patternsPromise = fetchPatterns().catch(() => INSPIRATION_SHORTS);
      const analysesPromise = fetchAnalyses().catch(() => []);

      const [manifestsList, patternsList, analysesList] = await Promise.all([
        manifestsPromise,
        patternsPromise,
        analysesPromise,
      ]);
      if (manifestsList && manifestsList.length > 0) setManifests(manifestsList);
      if (patternsList && patternsList.length > 0) setPatterns(patternsList);
      if (analysesList && analysesList.length > 0) setAnalyses(analysesList);
    } catch (err: any) {
      console.warn('Initial data load error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadManifestDetails = async (filename: string) => {
    try {
      setErrorMsg(null);
      const data = await fetchManifest(filename);
      setCurrentManifest(data);

      const promptText =
        data.concept_summary ||
        data.intent_interpretation?.story_summary ||
        data.title ||
        '';

      setActiveBrief({
        script: promptText,
        duration: data.total_target_duration_sec || 10.0,
        referenceTitle: data.title,
        activeDirectionTag: data.pattern_blueprint_id || data.visual_style_anchor,
      });
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleShotUpdate = (index: number, updatedShot: DirectorShotPlan) => {
    if (!currentManifest) return;
    const newShots = [...currentManifest.shots];
    newShots[index] = updatedShot;
    const totalDuration = newShots.reduce((acc, s) => acc + (s.duration_sec || 0), 0);
    setCurrentManifest({
      ...currentManifest,
      shots: newShots,
      total_target_duration_sec: totalDuration,
    });
  };

  const handleShotDelete = (index: number) => {
    if (!currentManifest) return;
    const newShots = currentManifest.shots.filter((_, i) => i !== index);
    const totalDuration = newShots.reduce((acc, s) => acc + (s.duration_sec || 0), 0);
    setCurrentManifest({
      ...currentManifest,
      shots: newShots,
      total_target_duration_sec: totalDuration,
    });
  };

  const handleAddShot = () => {
    if (!currentManifest) return;
    const nextIndex = currentManifest.shots.length + 1;
    const newShot: DirectorShotPlan = {
      shot_id: `shot_0${nextIndex}`,
      shot_index: nextIndex,
      beat_name: 'escalation',
      duration_sec: 2.5,
      is_hook_critical: false,
      visual: {
        format: 'b_roll',
        scene_description: 'Subject continues narrative progression with energetic dynamic action.',
        subject_action: 'Creator moves purposefully towards the camera.',
        framing: 'mcu',
        camera_movement: 'handheld',
        lighting: 'natural ambient daylight',
        color_grade: 'cinematic warm amber',
        face_expression: 'Engaged',
        gaze_direction: 'direct',
      },
      audio: {
        speech: {
          speaker: 'Creator',
          transcript: 'And that is where everything shifted.',
          vocal_delivery: 'natural',
          target_wpm: 150,
          emotion_tags: ['curious', 'engaging'],
          voice_id: null,
        },
        sfx_cues: [{ sfx_name: 'kinetic_whoosh', trigger_offset_sec: 0.0, volume_db: -3.0 }],
      },
      overlays: {
        captions: {
          text: 'And that is where everything shifted.',
          highlight_words: ['everything', 'shifted'],
          style: 'kinetic_captions',
          position: 'lower_third',
          animation: 'pop',
        },
        graphic_inserts: [],
      },
      transition_out: {
        transition_type: 'jump_cut',
        duration_ms: 0,
        vfx_snap_zoom: false,
        screen_shake: false,
      },
      applied_techniques: ['editing.jump_cut_cadence'],
    };
    const newShots = [...currentManifest.shots, newShot];
    const totalDuration = newShots.reduce((acc, s) => acc + (s.duration_sec || 0), 0);
    setCurrentManifest({
      ...currentManifest,
      shots: newShots,
      total_target_duration_sec: totalDuration,
    });
  };

  const handleRefineShot = async (index: number, instruction: string): Promise<string | void> => {
    if (!currentManifest) return;
    const targetShot = currentManifest.shots[index];
    setRefiningShotId(targetShot.shot_id);
    setErrorMsg(null);

    try {
      const result = await refineShot({
        shot: targetShot,
        shot_index: index,
        manifest: currentManifest,
        instruction,
        manifest_context: {
          title: currentManifest.title,
          visual_style_anchor: currentManifest.visual_style_anchor,
        },
      });
      if (result.shot) {
        handleShotUpdate(index, result.shot);
      }
      return result.explanation;
    } catch (err: any) {
      setErrorMsg(`Shot refinement error: ${err.message}`);
    } finally {
      setRefiningShotId(null);
    }
  };

  const handleDirect = async (params: DirectRequest) => {
    if (directAbortControllerRef.current) {
      directAbortControllerRef.current.abort();
    }
    const controller = new AbortController();
    directAbortControllerRef.current = controller;

    setIsDirecting(true);
    setErrorMsg(null);
    // Immediately preserve the user's prompt in activeBrief
    setActiveBrief((prev) => ({
      script: params.script,
      duration: params.duration || prev?.duration || 8.0,
      category: params.category || prev?.category,
      referenceTitle: prev?.referenceTitle,
      referenceVideoId: params.reference_video_id || prev?.referenceVideoId,
      activeDirectionTag: params.active_direction_tag || prev?.activeDirectionTag,
    }));
    try {
      const manifest = await directVideo(params, controller.signal);
      setCurrentManifest(manifest);
      // Ensure activeBrief retains user's prompt or manifest title/concept summary
      setActiveBrief((prev) => ({
        script: params.script || manifest.concept_summary || prev?.script || '',
        duration: manifest.total_target_duration_sec || params.duration || prev?.duration || 8.0,
        category: params.category || prev?.category,
        referenceTitle: prev?.referenceTitle || manifest.title,
        referenceVideoId: params.reference_video_id || prev?.referenceVideoId,
        activeDirectionTag: params.active_direction_tag || prev?.activeDirectionTag || manifest.pattern_blueprint_id,
      }));
      const updatedList = await fetchManifests();
      setManifests(updatedList);
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Directing request cancelled by client.');
        return;
      }
      setErrorMsg(err.message);
    } finally {
      setIsDirecting(false);
      if (directAbortControllerRef.current === controller) {
        directAbortControllerRef.current = null;
      }
    }
  };

  const handleSaveCurrentManifest = async () => {
    if (!currentManifest || isSaving) return;
    setIsSaving(true);
    setSaveStatus(null);
    try {
      await saveManifest(currentManifest);
      setSaveStatus('Saved!');
      setTimeout(() => setSaveStatus(null), 2500);
      const updatedList = await fetchManifests();
      setManifests(updatedList);
    } catch (err: any) {
      setErrorMsg(`Failed saving project: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyJson = async () => {
    if (!currentManifest) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(currentManifest, null, 2));
      setCopyStatus('Copied!');
      setTimeout(() => setCopyStatus(null), 2500);
    } catch {
      const textArea = document.createElement('textarea');
      textArea.value = JSON.stringify(currentManifest, null, 2);
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopyStatus('Copied!');
      setTimeout(() => setCopyStatus(null), 2500);
    }
  };

  const inspirationPatternsCount = patterns.filter(
    (p) => !p.pattern_id?.startsWith('pattern_reel_') && p.platform !== 'instagram_reels' && !(Array.isArray(p.source_video_ids) && p.source_video_ids[0]?.startsWith('ig_'))
  ).length;

  const handleOpenReferenceVideo = () => {
    if (!currentManifest) return;
    const dur = currentManifest.total_target_duration_sec || activeBrief?.duration || 0;
    if (dur > 10.0) {
      setErrorMsg(
        `Video cannot be generated: Timeline duration is ${dur.toFixed(1)}s. Reference video generation is only supported for durations up to 10 seconds. Please direct with 10s target duration.`
      );
      return;
    }
    setErrorMsg(null);
    setIsRefVideoModalOpen(true);
  };

  return (
    <div className="flex h-screen bg-[#030406] text-white overflow-hidden font-sans relative">
      {/* Interactive Three.js Ambient Film Reel Canvas */}
      <ThreeCanvas
        className="opacity-80"
        focalIndex={
          currentModule === 'home'
            ? homeFocalIndex
            : currentModule === 'director'
            ? 0
            : currentModule === 'analyser'
            ? 1
            : currentModule === 'content'
            ? 2
            : 3
        }
      />

      {/* Cinematic reel overlay: atmospheric lens vignette & telemetry */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-black/80 to-transparent"></div>
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/90 to-transparent"></div>
        <div className="absolute right-6 bottom-3 font-mono text-[10px] tracking-widest text-white/30 hidden lg:block">
          35MM · 24 FPS · LIVE REEL
        </div>
      </div>

      {/* Main Studio Viewport */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden relative z-10 text-white">
        {/* Pull Focus Out Header: Visible on each feature page to return home */}
        {currentModule !== 'home' && (
          <header className="min-h-14 py-2 px-3 sm:px-6 md:px-8 border-b border-white/10 flex items-center justify-between gap-2 bg-[#080a10]/80 shrink-0 z-30 select-none backdrop-blur-xl">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              <div className="flex items-center gap-2 px-2.5 sm:px-3.5 py-1 sm:py-1.5 bg-black/60 border border-white/10 rounded-full backdrop-blur-md shrink-0">
                <span
                  className={`w-2 h-2 rounded-full animate-pulse shrink-0 ${
                    currentModule === 'director'
                      ? 'bg-cyan-400'
                      : currentModule === 'analyser'
                      ? 'bg-purple-400'
                      : currentModule === 'content'
                      ? 'bg-pink-400'
                      : 'bg-amber-400'
                  }`}
                />
                <span className="font-mono text-[11px] sm:text-xs text-zinc-300 font-semibold tracking-wider uppercase truncate max-w-[130px] sm:max-w-none">
                  {currentModule === 'director'
                    ? 'AI Director Studio'
                    : currentModule === 'analyser'
                    ? 'Video Analyser'
                    : currentModule === 'content'
                    ? 'Creator DNA Vault'
                    : 'Inspiration Playbook'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
              {/* Feature specific actions */}
              {currentModule === 'director' && currentManifest && (
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <button
                    onClick={handleOpenReferenceVideo}
                    className="px-2.5 sm:px-3.5 py-1.5 rounded-xl text-[11px] sm:text-xs font-bold tracking-wider font-mono transition-all flex items-center gap-1.5 shadow-lg shadow-lime-300/15 active:scale-95 bg-gradient-to-r from-lime-300 to-emerald-300 hover:brightness-110 text-black cursor-pointer"
                    title="Preview reference footage or render Gemini Omni 1.1 Flash generation"
                  >
                    <Play className="w-3.5 h-3.5 fill-black shrink-0" />
                    <span className="hidden md:inline">Preview Omni</span>
                  </button>

                  <button
                    onClick={handleCopyJson}
                    className="px-2.5 sm:px-3 py-1.5 rounded-xl text-[11px] sm:text-xs font-mono transition-all flex items-center gap-1.5 shadow-sm active:scale-95 border cursor-pointer bg-black/60 hover:bg-white/10 text-zinc-200 border-white/10"
                    title="Copy production manifest JSON to clipboard"
                  >
                    {copyStatus ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-300 shrink-0" />
                        <span className="font-semibold text-emerald-300 hidden sm:inline">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                        <span className="hidden sm:inline">Copy JSON</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* PULL FOCUS OUT Button */}
              <button
                onClick={handleGoBack}
                className="px-3.5 sm:px-4 py-1.5 sm:py-2 glass-hud hover:border-cyan-400/50 text-xs font-semibold rounded-xl text-zinc-200 transition-all flex items-center gap-2 cursor-pointer shadow-lg active:scale-95 hover:bg-white/10 font-mono tracking-wider shrink-0"
                title="Return to home screen"
              >
                <span>←</span> PULL FOCUS OUT
              </button>
            </div>
          </header>
        )}

        {/* Global Error Banner */}
        {errorMsg && (
          <div className="px-6 py-2.5 bg-rose-950/80 border-b border-rose-500/30 text-rose-300 text-xs flex items-center justify-between z-20 backdrop-blur-md">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-white cursor-pointer">✕</button>
          </div>
        )}

        {/* VIEW 1: HOME PAGE WITH 4 SIGNATURE BOXES */}
        {currentModule === 'home' && (
          <div className="flex-1 overflow-y-auto custom-scroll flex flex-col relative z-10 animate-fade-in">
            <HomePage
              onNavigate={handleNavigate}
              manifestsCount={manifests.length}
              corpusCount={analyses.length}
              patternsCount={inspirationPatternsCount}
              userProfile={userProfile}
              onOpenGoogleAuth={() => setIsAuthModalOpen(true)}
              onFocalChange={setHomeFocalIndex}
            />
          </div>
        )}

        {/* VIEW 2: AI DIRECTOR */}
        {currentModule === 'director' && (
          <main className="flex-1 overflow-y-auto custom-scroll p-6 lg:p-8 relative z-10 animate-fade-in">
            {isDirecting && !currentManifest ? (
              /* High-polish Directing Progress State */
              <div className="w-full max-w-xl mx-auto py-16 flex flex-col items-center justify-center gap-6 text-center animate-fade-in">
                <div className="w-16 h-16 rounded-3xl bg-cyan-500/10 border-2 border-cyan-400/40 flex items-center justify-center shadow-lg shadow-cyan-500/20 relative">
                  <Sparkles className="w-8 h-8 text-cyan-400 animate-spin" />
                  <div className="absolute -inset-1 rounded-3xl border-2 border-cyan-400/30 animate-ping" />
                </div>
                <div>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-400/40 mb-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>AI DIRECTOR // DIRECTING SHORT</span>
                  </div>
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    Synthesizing Style-Transfer Contract
                  </h2>
                  {activeBrief?.referenceTitle && (
                    <p className="text-xs text-cyan-400 font-mono mt-1 font-semibold">
                      Style Source: "{activeBrief.referenceTitle}"
                      {activeBrief.activeDirectionTag ? ` • Modifier: ${activeBrief.activeDirectionTag}` : ''}
                    </p>
                  )}
                  {activeBrief?.script && (
                    <div className="mt-3 p-3.5 glass-hud rounded-xl text-xs text-zinc-300 italic max-w-md mx-auto shadow-xs leading-relaxed text-left border border-white/10">
                      <span className="text-[10px] font-bold text-zinc-500 not-italic block uppercase font-mono mb-1">
                        Your Story / Idea:
                      </span>
                      "{activeBrief.script}"
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2.5 text-[11px] font-mono text-zinc-400 bg-black/60 px-4 py-2 rounded-xl border border-white/10">
                  <span className="text-emerald-400 font-semibold">✓ Style Invariants</span>
                  <span>→</span>
                  <span className="text-cyan-400 font-bold animate-pulse">⚡ Beat Allocation & Pacing</span>
                  <span>→</span>
                  <span>Shot Continuity</span>
                </div>

                <button
                  onClick={() => resetDirectorState()}
                  className="mt-2 px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-xs font-mono font-semibold transition-all shadow-xs cursor-pointer flex items-center gap-1.5 active:scale-95"
                  title="Cancel directing and return to prompt"
                >
                  <XCircle className="w-3.5 h-3.5 text-rose-400" />
                  <span>Cancel Directing</span>
                </button>
              </div>
            ) : !currentManifest ? (
              /* Initial State: Only Director Briefing centered */
              <div className="w-full max-w-2xl mx-auto py-8">
                <PromptPanel
                  onDirect={handleDirect}
                  isLoading={isDirecting}
                  initialScript={activeBrief?.script}
                  initialDuration={activeBrief?.duration}
                  initialCategory={activeBrief?.category}
                  referenceTitle={activeBrief?.referenceTitle}
                  referenceVideoId={activeBrief?.referenceVideoId}
                  activeDirectionTag={activeBrief?.activeDirectionTag}
                  onScriptChange={(newScript) => {
                    setActiveBrief((prev) => ({
                      ...(prev || { duration: 8 }),
                      script: newScript,
                    }));
                  }}
                  onDurationChange={(newDuration) => {
                    setActiveBrief((prev) => ({
                      ...(prev || { script: '' }),
                      duration: newDuration,
                    }));
                  }}
                />
              </div>
            ) : (
              /* Manifest Ready: Two-column production workspace */
              <div className="grid grid-cols-12 gap-8">
                {/* LEFT COLUMN: Director Briefing */}
                <section className="col-span-12 lg:col-span-5 flex flex-col gap-6">
                  <PromptPanel
                    onDirect={handleDirect}
                    isLoading={isDirecting}
                    initialScript={activeBrief?.script}
                    initialDuration={activeBrief?.duration}
                    initialCategory={activeBrief?.category}
                    referenceTitle={activeBrief?.referenceTitle}
                    referenceVideoId={activeBrief?.referenceVideoId}
                    activeDirectionTag={activeBrief?.activeDirectionTag}
                    onScriptChange={(newScript) => {
                      setActiveBrief((prev) => ({
                        ...(prev || { duration: 8 }),
                        script: newScript,
                      }));
                    }}
                    onDurationChange={(newDuration) => {
                      setActiveBrief((prev) => ({
                        ...(prev || { script: '' }),
                        duration: newDuration,
                      }));
                    }}
                  />
                </section>

                {/* RIGHT COLUMN: Production Plan & Shot Sequence */}
                <section className="col-span-12 lg:col-span-7 flex flex-col gap-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 glass-hud p-4 rounded-2xl border border-white/10 backdrop-blur-xl shadow-2xl">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs uppercase font-mono tracking-widest text-zinc-200 font-bold">
                          Production Plan & Shot Sequence
                        </span>
                        <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-white/5 text-zinc-300 border border-white/10">
                          {currentManifest.shots.length} shots
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 mt-0.5">
                        Direct scene visuals, optics, dialogue, and applied filmmaking techniques.
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5 font-mono text-xs text-cyan-300 bg-cyan-500/10 px-3 py-1.5 rounded-xl border border-cyan-400/30 shadow-xs">
                        <Clock className="w-3.5 h-3.5 text-cyan-400" />
                        <span>{currentManifest.total_target_duration_sec.toFixed(1)}s</span>
                      </div>

                      <button
                        onClick={handleSaveCurrentManifest}
                        disabled={isSaving}
                        className="px-3 py-1.5 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-400/30 text-xs font-mono font-medium transition-all flex items-center gap-1.5 shadow-sm active:scale-95 cursor-pointer disabled:opacity-50"
                        title="Save project changes to your session archive"
                      >
                        {saveStatus ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-300" />
                            <span>Saved!</span>
                          </>
                        ) : (
                          <>
                            <Save className="w-3.5 h-3.5 text-emerald-400" />
                            <span>{isSaving ? 'Saving...' : 'Save Edits'}</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={handleAddShot}
                        className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-lime-300 to-emerald-300 hover:brightness-110 text-black text-xs font-mono font-bold tracking-wider transition-all flex items-center gap-1.5 shadow-lg shadow-lime-300/15 active:scale-95 cursor-pointer"
                        title="Add a new shot to the end of the sequence"
                      >
                        <Plus className="w-3.5 h-3.5 text-black" />
                        <span>Add Shot</span>
                      </button>

                      <button
                        onClick={() => resetDirectorState()}
                        className="px-2.5 py-1.5 rounded-xl bg-black/60 hover:bg-white/10 text-zinc-400 hover:text-white border border-white/10 text-xs font-mono font-medium transition-all flex items-center gap-1.5 shadow-sm active:scale-95 cursor-pointer"
                        title="Clear current manifest storyboard and start a new pitch"
                      >
                        <RotateCcw className="w-3.5 h-3.5 text-zinc-400" />
                        <span className="hidden sm:inline">New Pitch</span>
                      </button>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {currentManifest.shots.map((shot, idx) => (
                      <ShotCard
                        key={shot.shot_id || idx}
                        shot={shot}
                        index={idx}
                        onUpdate={(updated) => handleShotUpdate(idx, updated)}
                        onDelete={() => handleShotDelete(idx)}
                        onRefineChat={(instruction) => handleRefineShot(idx, instruction)}
                        isRefining={refiningShotId === shot.shot_id}
                      />
                    ))}

                    <button
                      onClick={handleAddShot}
                      className="w-full py-4 border-2 border-dashed border-white/15 hover:border-cyan-400/50 bg-black/40 hover:bg-cyan-500/5 rounded-2xl flex items-center justify-center gap-2 text-xs font-mono font-medium text-zinc-400 hover:text-cyan-300 transition-all group shadow-xs cursor-pointer active:scale-[0.99]"
                    >
                      <Plus className="w-4 h-4 text-zinc-500 group-hover:text-cyan-400 group-hover:scale-125 transition-all" />
                      <span>Add Shot ({`shot_${String(currentManifest.shots.length + 1).padStart(2, '0')}`})</span>
                    </button>
                  </div>
                </section>
              </div>
            )}
          </main>
        )}

        {/* VIEW 3: VIDEO ANALYSER */}
        {currentModule === 'analyser' && (
          <div className="flex-1 overflow-hidden flex flex-col relative z-10 animate-fade-in">
            <VideoAnalyser
              analyses={analyses}
              patterns={patterns}
              isLoading={isLoading}
              onDirectFromAnalysis={(options) => {
                const brief = {
                  script: options.userIdea,
                  duration: options.duration || 8.0,
                  category: options.category || 'lifestyle',
                  referenceTitle: options.referenceTitle,
                  referenceVideoId: options.referenceVideoId,
                  activeDirectionTag: options.activeDirectionTag,
                };
                setActiveBrief(brief);
                setCurrentManifest(null); // Clear previous manifest so director displays the new cut progress
                handleDirect({
                  script: options.userIdea,
                  creative_pitch: options.directorContextPrompt || `Match pacing cadence with viral hooks and style tags: ${(options.styleTags || []).join(', ')}`,
                  duration: options.duration || 8.0,
                  category: options.category || 'lifestyle',
                  style_tags: options.styleTags || [],
                  reference_video_id: options.referenceVideoId,
                  pattern_id: options.patternId,
                  active_direction_tag: options.activeDirectionTag,
                });
                handleNavigate('director');
              }}
            />
          </div>
        )}

        {/* VIEW 4: YOUR CONTENT */}
        {currentModule === 'content' && (
          <div className="flex-1 overflow-hidden flex flex-col relative z-10 animate-fade-in">
            <YourContent
              manifests={manifests}
              onOpenDirector={async (filename) => {
                await loadManifestDetails(filename);
                handleNavigate('director');
              }}
            />
          </div>
        )}

        {/* VIEW 5: INSPIRATION PLAYBOOK */}
        {currentModule === 'library' && (
          <div className="flex-1 overflow-hidden flex flex-col relative z-10 animate-fade-in">
            <ContentLibrary
              patterns={patterns}
              isLoading={isLoading}
              onUsePattern={(pattern, userIdea) => {
                const blueprintName = pattern.name || pattern.title || 'Viral Short';
                const hookFormula = pattern.hook_recipe?.formula || pattern.hook?.formula || '';
                const scriptText = userIdea?.trim()
                  ? userIdea.trim()
                  : `Direct an outlier short using the ${blueprintName} blueprint: ${hookFormula}`;
                const category = pattern.category || pattern.primary_category || 'lifestyle';
                const brief = {
                  script: scriptText,
                  duration: pattern.duration_sec || 8.0,
                  category,
                  referenceTitle: blueprintName,
                  activeDirectionTag: pattern.archetype || category,
                };
                setActiveBrief(brief);
                setCurrentManifest(null);

                handleDirect({
                  script: scriptText,
                  creative_pitch: `Apply ${blueprintName} blueprint. Hook formula: ${hookFormula}. Archetype: ${pattern.archetype || ''}`,
                  duration: pattern.duration_sec || 8.0,
                  category,
                  style_tags: pattern.style_tags || ['FAST-PACED', 'SFX-DRIVEN'],
                  pattern_id: pattern.pattern_id || pattern.video_id,
                  reference_video_id: pattern.video_id,
                });
                handleNavigate('director');
              }}
            />
          </div>
        )}

      </div>

      {/* Google OAuth & Creator DNA Modal */}
      <CreatorDNAModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        userProfile={userProfile}
        onUpdateProfile={setUserProfile}
      />

      {/* Reference Video Modal */}
      {currentManifest && (
        <ReferenceVideoModal
          isOpen={isRefVideoModalOpen}
          onClose={() => setIsRefVideoModalOpen(false)}
          manifest={currentManifest}
        />
      )}

    </div>
  );
}

export default App;
