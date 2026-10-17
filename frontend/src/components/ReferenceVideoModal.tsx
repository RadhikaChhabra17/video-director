import React, { useState, useRef } from 'react';
import {
  X,
  Film,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Play,
  UserCheck,
  XCircle,
} from 'lucide-react';
import { DirectorResponseManifest } from '../types/director';
import { renderReferenceVideo } from '../api/directorApi';

interface ReferenceVideoModalProps {
  manifest: DirectorResponseManifest;
  isOpen: boolean;
  onClose: () => void;
}

export const ReferenceVideoModal: React.FC<ReferenceVideoModalProps> = ({
  manifest,
  isOpen,
  onClose,
}) => {
  const [isRendering, setIsRendering] = useState<boolean>(false);
  const [renderedVideoUrl, setRenderedVideoUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [renderStep, setRenderStep] = useState<string>('Ready to synthesize');
  const abortControllerRef = useRef<AbortController | null>(null);

  const isDurationExceeded = (manifest.total_target_duration_sec || 0) > 10.0;

  if (!isOpen) return null;

  const handleCancelRender = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsRendering(false);
    setRenderStep('Generation cancelled');
  };

  const handleClose = () => {
    if (isRendering) {
      handleCancelRender();
    }
    onClose();
  };

  const handleStartRender = async () => {
    if (isDurationExceeded) {
      setErrorMsg(`Video cannot be generated: Duration (${manifest.total_target_duration_sec.toFixed(1)}s) exceeds 10s limit.`);
      return;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsRendering(true);
    setErrorMsg(null);
    setRenderedVideoUrl(null);
    setRenderStep('Synthesizing 10-second reference video with Gemini Omni 1.1 Flash...');

    try {
      const res = await renderReferenceVideo(
        {
          manifest,
          first_frame_path: null,
          use_default_character: true,
          resolution: '720p',
          aspect_ratio: '9:16',
          model: 'gemini-omni-1.1-flash-preview',
        },
        controller.signal
      );

      setRenderedVideoUrl(res.video_url);
      setRenderStep('Video successfully synthesized!');
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Omni generation cancelled by client');
        setRenderStep('Generation cancelled.');
        return;
      }
      setErrorMsg(`Video Generation error: ${err.message}`);
    } finally {
      setIsRendering(false);
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in">
      <div className="bg-[#080a10]/95 glass-hud rounded-3xl border border-white/10 w-full max-w-xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between bg-black/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-lime-500/15 text-lime-400 border border-lime-500/30 flex items-center justify-center shadow-lg">
              <Film className="w-5 h-5 text-lime-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Generate Reference Video
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-lime-500/15 text-lime-300 border border-lime-500/30 font-semibold">
                  Gemini Omni 1.1 Flash
                </span>
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Renders a visual prototype of "{manifest.title}".
              </p>
            </div>
          </div>

          <button
            onClick={handleClose}
            className="w-8 h-8 rounded-full hover:bg-white/10 flex items-center justify-center text-zinc-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto custom-scroll space-y-5 flex-1">
          {isDurationExceeded && (
            <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-500/40 text-xs text-rose-200 flex items-start gap-2.5 shadow-lg backdrop-blur-md">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold font-mono">Video cannot be generated</div>
                <div className="mt-0.5 text-[11px] text-rose-300 font-mono">
                  Timeline duration ({manifest.total_target_duration_sec.toFixed(1)}s) exceeds the 10.0s limit for reference video generation. Please direct a script with 10s target duration.
                </div>
              </div>
            </div>
          )}

          {errorMsg && !isDurationExceeded && (
            <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-500/40 text-xs text-rose-200 flex items-start gap-2.5 shadow-lg backdrop-blur-md">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 font-mono">{errorMsg}</div>
            </div>
          )}

          {/* If video is rendered, show it prominently */}
          {renderedVideoUrl && (
            <div className="p-6 rounded-3xl bg-emerald-950/40 border border-emerald-500/40 flex flex-col items-center gap-4 text-center shadow-xl">
              <div className="flex items-center gap-2 text-emerald-300 font-bold text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Reference Video Generated Successfully!</span>
              </div>

              <div className="w-full max-w-[280px] aspect-[9/16] bg-black rounded-2xl overflow-hidden shadow-2xl border border-white/20">
                <video
                  src={renderedVideoUrl}
                  controls
                  autoPlay
                  loop
                  className="w-full h-full object-contain"
                />
              </div>

              <a
                href={renderedVideoUrl}
                download={`${manifest.project_id}_omni_reference.mp4`}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-lime-300 to-emerald-300 text-black font-bold text-xs font-mono transition-all shadow-[0_0_15px_rgba(190,242,100,0.3)] hover:brightness-110 cursor-pointer"
              >
                Download MP4 Reference
              </a>
            </div>
          )}

          {/* AI Character Casting Card */}
          {!renderedVideoUrl && (
            <div className="p-5 rounded-3xl bg-black/50 border border-white/10 space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-lime-500/15 text-lime-400 flex items-center justify-center shrink-0 border border-lime-500/30 shadow-sm">
                  <UserCheck className="w-5 h-5 text-lime-400" />
                </div>
                <div>
                  <h4 className="text-xs font-bold font-mono text-white">
                    AI Character Casting: Let Omni Direct
                  </h4>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    Gemini Omni 1.1 Flash automatically casts and generates a realistic host suited to your script's narrative, lighting, and channel tone.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-[11px] font-mono text-lime-300 bg-lime-500/10 px-3 py-1.5 rounded-xl border border-lime-500/20">
                <Sparkles className="w-3.5 h-3.5 text-lime-400 shrink-0" />
                <span>Dynamic continuous motion from frame 0 with burned-in on-screen captions.</span>
              </div>
            </div>
          )}

          {/* Sequence Specs Preview */}
          {!renderedVideoUrl && (
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-3">
                <span className="font-bold text-white">{manifest.shots.length} Storyboard Shots</span>
                <span className="text-zinc-600">|</span>
                <span className="text-zinc-300">10s Video</span>
                <span className="text-zinc-600">|</span>
                <span className="text-zinc-300">9:16 Vertical</span>
              </div>
              <span className="text-lime-300 font-bold bg-lime-500/15 px-2 py-0.5 rounded border border-lime-500/30">
                Omni 1.1 Flash
              </span>
            </div>
          )}

          {/* Render In-Progress Indicator */}
          {isRendering && (
            <div className="p-6 rounded-3xl bg-cyan-950/40 border border-cyan-500/30 flex flex-col items-center justify-center text-center gap-3 animate-pulse">
              <div className="w-10 h-10 rounded-2xl bg-cyan-500/20 text-cyan-300 flex items-center justify-center border border-cyan-500/30">
                <Sparkles className="w-5 h-5 animate-spin" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-cyan-200 font-mono">Synthesizing with Gemini Omni 1.1 Flash</h4>
                <p className="text-[11px] text-cyan-300/80 mt-1">{renderStep}</p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-6 border-t border-white/10 flex items-center justify-between bg-black/40">
          <button
            onClick={handleClose}
            className="px-4 py-2 rounded-xl text-xs font-mono font-medium text-zinc-400 hover:text-white transition-colors cursor-pointer"
          >
            Close
          </button>

          {isRendering && (
            <button
              onClick={handleCancelRender}
              className="px-4 py-2 rounded-xl bg-white/5 hover:bg-rose-500/10 text-rose-300 border border-rose-500/30 text-xs font-mono font-semibold transition-all shadow-xs cursor-pointer flex items-center gap-1.5 active:scale-95"
            >
              <XCircle className="w-3.5 h-3.5 text-rose-400" />
              <span>Cancel Generation</span>
            </button>
          )}

          {!renderedVideoUrl && !isRendering && (
            <button
              onClick={handleStartRender}
              disabled={isDurationExceeded}
              className={`px-5 py-2.5 rounded-xl font-mono font-bold text-xs flex items-center gap-2 shadow-md transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer ${
                isDurationExceeded
                  ? 'bg-rose-600 hover:bg-rose-500 text-white'
                  : 'bg-gradient-to-r from-lime-300 to-emerald-300 text-black border border-lime-300/40 hover:brightness-110 shadow-[0_0_20px_rgba(190,242,100,0.3)]'
              }`}
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{isDurationExceeded ? 'Duration Exceeds 10s Limit' : 'Render Omni Video'}</span>
            </button>
          )}
        </div>

      </div>
    </div>
  );
};
