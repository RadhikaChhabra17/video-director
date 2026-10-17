import React, { useState, useMemo, useEffect } from 'react';
import {
  Sparkles,
  Search,
  Play,
  ExternalLink,
  X,
  ArrowRight,
  Flame,
  ChevronDown,
  ChevronUp,
  SlidersHorizontal,
  Film,
  Zap,
  Loader2,
  Clock,
  RotateCw,
} from 'lucide-react';
import { fetchAnalysisDetail } from '../api/directorApi';

interface ContentLibraryProps {
  patterns: any[];
  isLoading: boolean;
  onUsePattern?: (pattern: any, userIdea?: string) => void;
}

// Crisp 1080p/720p HD Video Thumbnail with progressive fallback
const HDThumbnailImage: React.FC<{
  videoId: string;
  alt: string;
  fallbackThumbnail?: string;
}> = ({ videoId, alt, fallbackThumbnail }) => {
  const initialSrc = videoId
    ? `https://i.ytimg.com/vi/${videoId}/maxresdefault.jpg`
    : (fallbackThumbnail || '/sample_hero.png');
  const [src, setSrc] = useState(initialSrc);
  const [triedStep, setTriedStep] = useState(0);

  const handleError = () => {
    if (triedStep === 0 && videoId) {
      setTriedStep(1);
      setSrc(`https://i.ytimg.com/vi/${videoId}/sddefault.jpg`);
    } else if (triedStep === 1 && videoId) {
      setTriedStep(2);
      setSrc(`https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`);
    } else {
      setSrc('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=80');
    }
  };

  return (
    <img
      src={src}
      alt={alt}
      onError={handleError}
      className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
      loading="lazy"
      decoding="async"
    />
  );
};

// Check to exclude any non-YouTube or Instagram Reel entries from Inspiration
const isInstagramPattern = (p: any): boolean => {
  if (!p) return false;
  return Boolean(
    p.platform === 'instagram_reels' ||
    p.hero_video?.platform === 'instagram_reels' ||
    p.pattern_id?.startsWith('pattern_reel_') ||
    (Array.isArray(p.source_video_ids) && p.source_video_ids[0]?.startsWith('ig_')) ||
    (p.hero_video?.video_id && p.hero_video.video_id.startsWith('ig_')) ||
    (p.video_id && p.video_id.startsWith('ig_'))
  );
};

const formatViews = (num: number): string => {
  if (!num) return 'Viral';
  if (num >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1)}B views`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M views`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(0)}K views`;
  return `${num} views`;
};

export const ContentLibrary: React.FC<ContentLibraryProps> = ({
  patterns,
  isLoading,
  onUsePattern,
}) => {
  // Category & Sort Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNiche, setSelectedNiche] = useState('all');
  const [sortBy, setSortBy] = useState<'views' | 'duration'>('views');

  // Selected Video for Modal
  const [selectedVideo, setSelectedVideo] = useState<any | null>(null);
  const [remixIdea, setRemixIdea] = useState('');
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  // Dynamic On-Demand Multimodal Analysis State (Zero Disk Storage)
  const [liveAnalysis, setLiveAnalysis] = useState<any | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Progressive batching for instant client-side rendering (24 at a time)
  const [visibleCount, setVisibleCount] = useState(24);

  useEffect(() => {
    setVisibleCount(24);
  }, [selectedNiche, searchQuery, sortBy]);

  // Pure YouTube Shorts catalog for Inspiration
  const youtubeVideos = useMemo(() => {
    return patterns.filter((p) => !isInstagramPattern(p));
  }, [patterns]);

  // Extract unique niches for top filter bar
  const niches = useMemo(() => {
    const list = new Set<string>();
    youtubeVideos.forEach((p) => {
      const cat = (p.category || p.primary_category || '').toLowerCase().trim();
      if (cat && !/^\d+$/.test(cat)) {
        list.add(cat);
      }
    });
    return Array.from(list).sort();
  }, [youtubeVideos]);

  // Filter & Sort Videos (Metadata Only)
  const filteredVideos = useMemo(() => {
    return youtubeVideos
      .filter((p) => {
        const cat = (p.category || p.primary_category || '').toLowerCase().trim();
        if (/^\d+$/.test(cat)) return false;

        // Niche filter
        if (selectedNiche !== 'all' && cat !== selectedNiche) {
          return false;
        }

        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const title = (p.title || p.hero_video?.title || p.name || '').toLowerCase();
          const channel = (p.channel || p.hero_video?.channel || '').toLowerCase();
          const category = cat.toLowerCase();
          if (!title.includes(q) && !channel.includes(q) && !category.includes(q)) {
            return false;
          }
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'views') {
          const viewsA = a.views || a.hero_video?.views || a.aggregate_views || 0;
          const viewsB = b.views || b.hero_video?.views || b.aggregate_views || 0;
          return viewsB - viewsA;
        }
        if (sortBy === 'duration') {
          const durA = a.duration_sec || a.duration || 15;
          const durB = b.duration_sec || b.duration || 15;
          return durB - durA;
        }
        return 0;
      });
  }, [youtubeVideos, selectedNiche, searchQuery, sortBy]);

  // Fast windowed slice of videos for instant rendering
  const visibleVideos = useMemo(() => {
    return filteredVideos.slice(0, visibleCount);
  }, [filteredVideos, visibleCount]);

  // Trigger On-Demand Multimodal Analysis on Video Click
  const handleOpenVideo = (video: any) => {
    setSelectedVideo(video);
    setRemixIdea('');
    setShowTechnicalDetails(false);
    setLiveAnalysis(null);
    setAnalysisError(null);
    setIsAnalyzing(true);

    const vidId = video.video_id || video.hero_video?.video_id || (video.source_video_ids && video.source_video_ids[0]);
    if (vidId) {
      fetchAnalysisDetail(vidId)
        .then((data) => {
          setLiveAnalysis(data);
        })
        .catch((err: any) => {
          setAnalysisError(err.message || 'Failed to complete multimodal analysis');
        })
        .finally(() => {
          setIsAnalyzing(false);
        });
    } else {
      setIsAnalyzing(false);
    }
  };

  // Re-run dynamic analysis on demand
  const handleRetryAnalysis = async () => {
    if (!selectedVideo || isAnalyzing) return;
    const vidId = selectedVideo.video_id || selectedVideo.hero_video?.video_id || (selectedVideo.source_video_ids && selectedVideo.source_video_ids[0]);
    if (!vidId) return;

    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const data = await fetchAnalysisDetail(vidId);
      setLiveAnalysis(data);
    } catch (err: any) {
      setAnalysisError(err.message || 'Failed to complete on-demand analysis');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Launch Director Studio with the dynamically deconstructed blueprint
  const handleLaunchStudio = (video: any) => {
    if (onUsePattern) {
      const mergedBlueprint = {
        ...video,
        ...(liveAnalysis || {}),
        name: video.title || video.name,
        title: video.title || video.name,
        primary_category: video.category || video.primary_category || 'entertainment',
        hook_recipe: liveAnalysis?.hook_recipe || liveAnalysis?.hook || video.hook_recipe,
        director_guidelines: liveAnalysis?.director_guidelines || liveAnalysis?.tactical_guidelines || video.director_guidelines,
        archetype: liveAnalysis?.archetype || video.archetype,
        style_tags: liveAnalysis?.style_tags || video.style_tags || ['FAST-PACED', 'SFX-DRIVEN'],
      };
      onUsePattern(mergedBlueprint, remixIdea);
      setSelectedVideo(null);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto custom-scroll p-6 lg:p-8 flex flex-col gap-6">
      
      {/* 1. HERO HEADER */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase font-mono tracking-widest text-amber-300 font-bold flex items-center gap-1.5 bg-amber-500/15 px-2.5 py-0.5 rounded-full border border-amber-500/30">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Inspiration Catalog
            </span>
          </div>

          <h1 className="text-2xl lg:text-3xl font-extrabold text-white mt-2 tracking-tight">
            Where Viral Ideas Start
          </h1>
          <p className="text-xs text-zinc-400 mt-1 max-w-2xl leading-relaxed">
            Click any viral Short to trigger on-demand multimodal analysis. Gemini deconstructs the hook formula, pacing cadence, and camera movement dynamically.
          </p>
        </div>
      </div>

      {/* 2. CATEGORY PILLS & SEARCH BAR */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
        
        {/* Horizontal Niche Pill Bar */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 custom-scroll">
          <button
            onClick={() => setSelectedNiche('all')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all shadow-xs cursor-pointer ${
              selectedNiche === 'all'
                ? 'bg-gradient-to-r from-amber-400 to-orange-400 text-black shadow-md'
                : 'bg-white/5 hover:bg-white/10 text-zinc-300 border border-white/10'
            }`}
          >
            All Niches
          </button>

          {niches.map((niche) => (
            <button
              key={niche}
              onClick={() => setSelectedNiche(niche)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold capitalize whitespace-nowrap transition-all shadow-xs cursor-pointer ${
                selectedNiche === niche
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-400/50 shadow-[0_0_10px_rgba(245,158,11,0.2)] font-bold'
                  : 'bg-white/5 hover:bg-white/10 text-zinc-300 border border-white/10'
              }`}
            >
              <span>{niche}</span>
            </button>
          ))}
        </div>

        {/* Search & Sort Controls */}
        <div className="flex items-center gap-2 self-end lg:self-auto w-full lg:w-auto">
          <div className="relative flex-1 lg:w-64">
            <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by creator, title, category..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-black/60 border border-white/10 focus:outline-hidden focus:border-amber-400 text-white placeholder-zinc-500 font-sans shadow-inner"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white cursor-pointer"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-1 bg-black/60 px-2.5 py-1.5 rounded-xl border border-white/10 shadow-inner">
            <SlidersHorizontal className="w-3 h-3 text-zinc-400 shrink-0" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent text-zinc-200 font-mono text-xs focus:outline-hidden cursor-pointer"
            >
              <option value="views" className="bg-[#0b0e17] text-white">Most Views</option>
              <option value="duration" className="bg-[#0b0e17] text-white">Duration</option>
            </select>
          </div>
        </div>
      </div>

      {/* 3. LIGHTWEIGHT VIDEO WALL GRID */}
      {isLoading && youtubeVideos.length === 0 ? (
        <div className="py-24 text-center font-mono text-xs text-zinc-400 flex flex-col items-center justify-center gap-3">
          <div className="w-7 h-7 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading viral video catalog...</span>
        </div>
      ) : filteredVideos.length === 0 ? (
        <div className="py-20 text-center font-mono text-xs text-zinc-400 bg-[#080a10]/70 rounded-2xl border border-dashed border-white/10 p-8 glass-hud">
          <p className="font-semibold text-zinc-200">No videos match your search or filter.</p>
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedNiche('all');
            }}
            className="mt-3 px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-400/40 font-semibold hover:bg-amber-500/30 transition-colors cursor-pointer"
          >
            Clear Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-4 gap-5">
          {visibleVideos.map((video) => {
            const vidId = video.video_id || video.hero_video?.video_id || (video.source_video_ids && video.source_video_ids[0]) || '';
            const title = video.title || video.hero_video?.title || video.name || 'Viral Short';
            const channel = video.channel || video.hero_video?.channel || 'Creator';
            const category = video.category || video.primary_category || 'viral';
            const duration = video.duration_sec || video.duration || 15;
            const views = video.views || video.hero_video?.views || video.aggregate_views || 0;

            return (
              <div
                key={vidId}
                onClick={() => handleOpenVideo(video)}
                className="aspect-[9/16] rounded-2xl overflow-hidden relative group cursor-pointer shadow-xl hover:shadow-[0_0_25px_rgba(245,158,11,0.25)] transition-all duration-300 border border-white/10 hover:border-amber-400/60 bg-black flex flex-col justify-between"
              >
                {/* 1. 1080p HD YouTube Thumbnail with progressive fallback */}
                <HDThumbnailImage
                  videoId={vidId}
                  alt={title}
                  fallbackThumbnail={video.thumbnail || video.hero_video?.thumbnail}
                />

                {/* 2. Sleek Vignette Gradients */}
                <div className="absolute inset-0 bg-gradient-to-b from-black/85 via-transparent to-black/95 pointer-events-none" />

                {/* 3. Top Floating Badges (Category & Duration & Views) */}
                <div className="relative z-10 p-3.5 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/15 backdrop-blur-md text-white font-bold uppercase tracking-wider border border-white/20">
                      {category}
                    </span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-md backdrop-blur-md font-bold bg-white/20 text-white flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5" />
                      {Math.round(duration)}s
                    </span>
                  </div>

                  <span className="text-[10px] font-mono font-bold text-amber-300 bg-black/70 backdrop-blur-md px-2 py-0.5 rounded-full border border-amber-400/30 flex items-center gap-1">
                    <Flame className="w-3 h-3 text-amber-400 fill-amber-400" />
                    {formatViews(views)}
                  </span>
                </div>

                {/* 4. Center Play Pill on Hover */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-12 h-12 rounded-full bg-black/50 backdrop-blur-md border border-white/30 text-white group-hover:bg-gradient-to-r group-hover:from-amber-400 group-hover:to-orange-400 group-hover:text-black group-hover:border-amber-400 flex items-center justify-center transition-all duration-300 opacity-60 group-hover:opacity-100 group-hover:scale-110 shadow-2xl">
                    <Play className="w-5 h-5 ml-0.5 fill-current" />
                  </div>
                </div>

                {/* 5. Bottom Overlay: Clean Creator Handle & Video Title */}
                <div className="relative z-10 p-4 flex flex-col gap-1.5">
                  {channel && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-mono font-bold text-emerald-400 truncate drop-shadow-sm">
                        @{channel.replace('@', '')}
                      </span>
                    </div>
                  )}

                  <h3 className="text-xs font-bold text-white leading-snug line-clamp-2 drop-shadow-md">
                    {title}
                  </h3>

                  {/* Clean Hover Action Button */}
                  <div className="mt-1 pt-2 border-t border-white/15 flex items-center justify-between text-white text-xs font-semibold group-hover:text-amber-300 transition-colors">
                    <span className="text-[11px] font-mono">Watch & Analyze</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>

              </div>
            );
          })}
        </div>
      )}

      {/* Progressive Load More Controls */}
      {visibleCount < filteredVideos.length && (
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-6 pb-4">
          <button
            onClick={() => setVisibleCount((prev) => Math.min(prev + 24, filteredVideos.length))}
            className="px-6 py-2.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-400/40 font-mono text-xs font-semibold transition-all shadow-md active:scale-95 flex items-center gap-2 cursor-pointer"
          >
            <span>Load More Shorts</span>
          </button>
          <button
            onClick={() => setVisibleCount(filteredVideos.length)}
            className="px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-zinc-300 font-mono text-xs font-semibold border border-white/10 transition-all shadow-xs cursor-pointer"
          >
            Show All
          </button>
        </div>
      )}

      {/* 4. ON-CLICK ANALYSIS & PLAYER MODAL */}
      {selectedVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 sm:p-6 animate-fade-in">
          
          {/* Modal Container */}
          <div className="relative w-full max-w-4xl bg-[#080a10]/95 glass-hud rounded-3xl overflow-hidden shadow-2xl border border-white/10 flex flex-col md:flex-row max-h-[92vh]">
            
            {/* Close Button */}
            <button
              onClick={() => setSelectedVideo(null)}
              className="absolute top-4 right-4 z-30 w-9 h-9 rounded-full bg-black/70 hover:bg-black text-white flex items-center justify-center transition-all border border-white/20 cursor-pointer shadow-lg"
            >
              <X className="w-4 h-4" />
            </button>

            {/* LEFT COLUMN: 9:16 Video Player Embed */}
            {(() => {
              const activeVidId = selectedVideo.video_id || selectedVideo.hero_video?.video_id || (selectedVideo.source_video_ids && selectedVideo.source_video_ids[0]) || '';
              const activeYtUrl = selectedVideo.url || selectedVideo.hero_video?.url || `https://www.youtube.com/shorts/${activeVidId}`;

              return (
                <div className="w-full md:w-[380px] bg-black aspect-[9/16] shrink-0 flex flex-col relative border-b md:border-b-0 md:border-r border-white/10">
                  <iframe
                    src={`https://www.youtube-nocookie.com/embed/${activeVidId}?autoplay=1&rel=0&modestbranding=1&vq=hd1080&playsinline=1`}
                    title={selectedVideo.title || selectedVideo.hero_video?.title || 'Viral Short'}
                    className="w-full h-full border-0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowFullScreen
                  />

                  {/* Video Sub-bar */}
                  <div className="p-3 bg-black/90 border-t border-white/10 flex items-center justify-between text-[11px] font-mono text-white shrink-0">
                    <span className="truncate max-w-[180px] text-emerald-400 font-semibold">
                      @{selectedVideo.channel || selectedVideo.hero_video?.channel || 'Creator'}
                    </span>
                    <div className="flex items-center gap-2.5">
                      <span className="text-zinc-300 font-bold flex items-center gap-1">
                        <Flame className="w-3 h-3 text-amber-400 fill-amber-400" />
                        Viral Short
                      </span>
                      <a
                        href={activeYtUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1 rounded bg-white/10 hover:bg-white/20 text-white transition-colors flex items-center gap-1 text-[10px] cursor-pointer"
                        title="Open Short directly on YouTube in Full HD"
                      >
                        <span>YouTube</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* RIGHT COLUMN: Clean Progress State or Deconstructed Blueprint */}
            <div className="flex-1 flex flex-col justify-between p-6 md:p-8 overflow-y-auto custom-scroll bg-[#0b0e17]/90 text-zinc-200">
              
              {/* STATE A: Loading Analysis Progress */}
              {isAnalyzing && (
                <div className="flex-1 flex flex-col items-center justify-center p-8 gap-4 text-center my-auto min-h-[350px]">
                  <div className="relative">
                    <div className="w-16 h-16 rounded-3xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center shadow-lg animate-pulse">
                      <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                    </div>
                    <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-gradient-to-r from-lime-300 to-emerald-300 text-black flex items-center justify-center text-[10px] font-bold shadow-md">
                      <Zap className="w-3.5 h-3.5 fill-black" />
                    </div>
                  </div>

                  <div className="space-y-1.5 max-w-sm">
                    <h3 className="text-sm font-bold font-mono text-white tracking-tight">
                      Analyzing visual rhythm & hook formula...
                    </h3>
                    <p className="text-xs text-zinc-400 font-mono leading-relaxed">
                      Deconstructing hook (first 3s), pacing cadence, camera framing, and audio/SFX cues
                    </p>
                  </div>

                  {/* Gradient pulse progress bar */}
                  <div className="w-64 h-1.5 bg-white/10 rounded-full overflow-hidden mt-1">
                    <div className="h-full bg-gradient-to-r from-amber-400 via-purple-500 to-cyan-400 rounded-full animate-pulse w-3/4"></div>
                  </div>

                  <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-400 mt-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                    <span>Streaming frames & telemetry via Gemini</span>
                  </div>
                </div>
              )}

              {/* STATE B: Error State with Retry Button */}
              {!isAnalyzing && analysisError && (
                <div className="flex-1 flex flex-col items-center justify-center p-8 gap-3 text-center my-auto min-h-[300px]">
                  <div className="w-12 h-12 rounded-2xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
                    <X className="w-6 h-6" />
                  </div>
                  <p className="text-xs font-mono font-bold text-rose-300">{analysisError}</p>
                  <button
                    onClick={handleRetryAnalysis}
                    className="mt-2 px-4 py-2 rounded-xl text-xs font-mono font-bold bg-white/10 hover:bg-white/20 text-white border border-white/15 transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
                  >
                    <RotateCw className="w-3 h-3" />
                    <span>Retry Analysis</span>
                  </button>
                </div>
              )}

              {/* STATE C: Deconstructed Blueprint Display (Exact Layout as Before) */}
              {!isAnalyzing && !analysisError && (
                <div className="flex flex-col gap-4">
                  
                  {/* Header Tag & Title */}
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-bold uppercase tracking-wider">
                        {selectedVideo.category || selectedVideo.primary_category || 'entertainment'}
                      </span>
                      <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-white/5 text-zinc-300 border border-white/10 capitalize">
                        {selectedVideo.creator_setup || liveAnalysis?.creator_setup || 'solo'}
                      </span>
                      <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-white/5 text-zinc-300 border border-white/10">
                        YouTube Short
                      </span>
                    </div>

                    <h2 className="text-xl font-extrabold text-white mt-2">
                      {selectedVideo.name || selectedVideo.title || selectedVideo.hero_video?.title}
                    </h2>
                    <p className="text-xs text-zinc-300 mt-1 leading-relaxed">
                      {liveAnalysis?.archetype || selectedVideo.archetype || 'A high-energy surprise challenge where a creator enters an unsuspecting environment with a massive reward, driving intense curiosity and emotional payoff through rapid pacing and immersive framing.'}
                    </p>
                  </div>

                  {/* 1. THE SCROLL-STOPPER (FIRST 3 SECONDS) */}
                  <div className="bg-black/50 p-4 rounded-2xl border border-white/10 shadow-lg flex flex-col gap-2">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 font-bold flex items-center gap-1.5">
                      <Flame className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                      The Scroll-Stopper (First 3 Seconds)
                    </span>

                    <p className="text-xs text-white font-medium leading-relaxed">
                      {liveAnalysis?.hook?.first_3s_action || liveAnalysis?.hook_recipe?.first_3s_action || selectedVideo.hook_recipe?.first_3s_action || 'Creator walks down a hallway holding an oversized visual prop while speaking directly to the camera with deadpan intensity before opening a door into a room.'}
                    </p>

                    {(liveAnalysis?.hook?.formula || liveAnalysis?.hook_recipe?.formula || selectedVideo.hook_recipe?.formula) && (
                      <div className="bg-amber-950/30 p-2.5 rounded-xl border border-amber-500/30 mt-1">
                        <p className="text-[11px] font-mono text-amber-300">
                          Formula: {liveAnalysis?.hook?.formula || liveAnalysis?.hook_recipe?.formula || selectedVideo.hook_recipe?.formula}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* 2. GREAT FOR TOPICS */}
                  {(() => {
                    const topics = (liveAnalysis?.best_use_cases && liveAnalysis.best_use_cases.length > 0)
                      ? liveAnalysis.best_use_cases
                      : (selectedVideo.best_use_cases && selectedVideo.best_use_cases.length > 0)
                      ? selectedVideo.best_use_cases
                      : [
                          'Surprise public cash give-aways',
                          'High-stakes classroom challenges',
                          'Impromptu street game shows',
                        ];

                    return (
                      <div>
                        <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-bold block mb-1.5">
                          Great for Topics:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {topics.map((useCase: string) => (
                            <span
                              key={useCase}
                              className="text-[11px] font-mono px-2.5 py-1 rounded-xl bg-white/5 text-zinc-200 border border-white/10 shadow-sm font-medium"
                            >
                              {useCase}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* 3. COLLAPSIBLE TACTICAL SHOOTING GUIDELINES */}
                  <div className="border border-white/10 rounded-xl overflow-hidden bg-black/40 mt-1">
                    <button
                      onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                      className="w-full px-3.5 py-2 text-xs font-mono text-zinc-300 hover:text-white flex items-center justify-between transition-colors bg-white/5 cursor-pointer"
                    >
                      <span className="flex items-center gap-1.5">
                        <Zap className="w-3.5 h-3.5 text-amber-400" />
                        View Tactical Shooting Guidelines
                      </span>
                      {showTechnicalDetails ? (
                        <ChevronUp className="w-3.5 h-3.5 text-zinc-400" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />
                      )}
                    </button>

                    {showTechnicalDetails && (
                      <div className="p-4 space-y-2 text-xs text-zinc-300 bg-black/50">
                        {(liveAnalysis?.tactical_guidelines || liveAnalysis?.director_guidelines || selectedVideo.director_guidelines || [
                          'Establish the grand scale of the physical setup immediately in the wide establishing shot.',
                          'Ensure physical action in the hook spans smoothly into tracking movement.',
                          'Keep energy high and vocal delivery authoritative yet deeply engaging.',
                          'Use strategic sound effects like whooshes and dings to accentuate reveals.',
                        ]).map((g: string, idx: number) => (
                          <div key={idx} className="flex items-start gap-2">
                            <span className="text-amber-400 font-bold">•</span>
                            <span>{g}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                </div>
              )}

              {/* BOTTOM: QUICK REMIX STUDIO LAUNCHER */}
              <div className="mt-6 pt-5 border-t border-white/10 flex flex-col gap-3">
                <span className="text-xs font-mono uppercase tracking-wider font-bold text-white flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  Direct with this Style
                </span>

                <textarea
                  value={remixIdea}
                  onChange={(e) => setRemixIdea(e.target.value)}
                  placeholder="Enter your topic (e.g. 3 counter-intuitive mistakes everyone makes when buying their first camera...)"
                  rows={2}
                  className="w-full p-3 text-xs rounded-xl bg-black/60 border border-white/10 focus:outline-hidden focus:border-amber-400 text-white placeholder-zinc-500 font-sans shadow-inner resize-none"
                />

                <button
                  onClick={() => handleLaunchStudio(selectedVideo)}
                  disabled={isAnalyzing}
                  className="w-full py-3 px-4 rounded-xl text-xs font-bold bg-gradient-to-r from-lime-300 to-emerald-300 text-black border border-lime-300/40 hover:brightness-110 active:scale-[0.99] transition-all shadow-[0_0_20px_rgba(190,242,100,0.3)] flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  <Film className="w-4 h-4 text-black" />
                  <span>Launch in Director Studio with this Blueprint</span>
                  <ArrowRight className="w-4 h-4 text-black" />
                </button>
              </div>

            </div>

          </div>
        </div>
      )}

    </div>
  );
};

export default ContentLibrary;
