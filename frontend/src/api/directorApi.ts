import {
  DirectorResponseManifest,
  ManifestSummary,
  DirectRequest,
  RefineShotRequest,
} from '../types/director';
import { INSPIRATION_SHORTS } from '../data/inspirationShorts';

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 2500): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(id);
    return res;
  } catch (err) {
    clearTimeout(id);
    throw err;
  }
}

// Retrieve or initialize a persistent, private session ID for this browser
export function getSessionId(): string {
  let sessionId = localStorage.getItem('director_session_id');
  if (!sessionId) {
    sessionId = 'sess_' + Math.random().toString(36).substring(2, 10) + '_' + Date.now().toString(36);
    localStorage.setItem('director_session_id', sessionId);
  }
  return sessionId;
}

async function safeParseError(res: Response, fallback: string): Promise<string> {
  try {
    const text = await res.text();
    try {
      const data = JSON.parse(text);
      if (Array.isArray(data.detail)) {
        return data.detail
          .map((item: any) => {
            const loc = Array.isArray(item.loc)
              ? item.loc.filter((x: any) => x !== 'body').join('.')
              : '';
            return loc ? `${loc}: ${item.msg || item}` : (item.msg || JSON.stringify(item));
          })
          .join('; ');
      }
      if (typeof data.detail === 'string') return data.detail;
      if (data.detail && typeof data.detail === 'object') return JSON.stringify(data.detail);
      if (typeof data.error === 'string') return data.error;
      if (data.error && typeof data.error === 'object') return JSON.stringify(data.error);
      if (typeof data.message === 'string') return data.message;
      return fallback;
    } catch {
      if (text && text.trim()) {
        return text.trim();
      }
    }
  } catch {}
  return `${fallback} (HTTP ${res.status}: ${res.statusText || 'Error'})`;
}

export async function fetchManifests(): Promise<ManifestSummary[]> {
  try {
    const sessionId = getSessionId();
    const res = await fetchWithTimeout(`/api/manifests?session_id=${encodeURIComponent(sessionId)}`, {
      headers: { 'X-Session-ID': sessionId },
    }, 2500);
    if (!res.ok) return [];
    const data = await res.json();
    return data.manifests || [];
  } catch {
    return [];
  }
}

export async function fetchManifest(filename: string): Promise<DirectorResponseManifest> {
  const sessionId = getSessionId();
  const res = await fetch(`/api/manifest/${encodeURIComponent(filename)}?session_id=${encodeURIComponent(sessionId)}`, {
    headers: { 'X-Session-ID': sessionId },
  });
  if (!res.ok) {
    const errMsg = await safeParseError(res, `Failed to load manifest ${filename}`);
    throw new Error(errMsg);
  }
  return res.json();
}

export async function saveManifest(manifest: DirectorResponseManifest): Promise<{ status: string; filename: string }> {
  const sessionId = getSessionId();
  const res = await fetch('/api/save-manifest', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId,
    },
    body: JSON.stringify({ manifest, session_id: sessionId }),
  });
  if (!res.ok) {
    const errMsg = await safeParseError(res, 'Failed to save manifest');
    throw new Error(errMsg);
  }
  return res.json();
}

export async function uploadCharacterPhoto(file: File): Promise<{
  status: string;
  filename: string;
  local_path: string;
  photo_url: string;
}> {
  const sessionId = getSessionId();
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/api/upload-character-photo', {
    method: 'POST',
    headers: {
      'X-Session-ID': sessionId,
    },
    body: formData,
  });

  if (!res.ok) {
    const errMsg = await safeParseError(res, 'Failed to upload photo');
    throw new Error(errMsg);
  }
  return res.json();
}

export interface RenderVideoParams {
  manifest: DirectorResponseManifest;
  first_frame_path?: string | null;
  use_default_character?: boolean;
  resolution?: string;
  aspect_ratio?: string;
  model?: string;
}

export async function renderReferenceVideo(
  params: RenderVideoParams,
  signal?: AbortSignal
): Promise<{
  status: string;
  video_url: string;
  filename: string;
  local_path: string;
  used_character_photo: boolean;
}> {
  const sessionId = getSessionId();
  const res = await fetch('/api/render-reference-video', {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId,
    },
    body: JSON.stringify({
      ...params,
      session_id: sessionId,
    }),
  });

  if (!res.ok) {
    const errMsg = await safeParseError(res, 'Video generation failed');
    throw new Error(errMsg);
  }
  return res.json();
}

export async function cancelDirect(): Promise<void> {
  try {
    const sessionId = getSessionId();
    await fetch('/api/cancel-direct', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,
      },
      body: JSON.stringify({ session_id: sessionId }),
    });
  } catch {
    // Non-blocking best effort cancellation
  }
}

export async function directVideo(params: DirectRequest, signal?: AbortSignal): Promise<DirectorResponseManifest> {
  const sessionId = getSessionId();
  const res = await fetch('/api/direct', {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId,
    },
    body: JSON.stringify({ ...params, session_id: sessionId }),
  });
  if (!res.ok) {
    const errMsg = await safeParseError(res, 'Failed to generate director cut');
    throw new Error(errMsg);
  }
  const data = await res.json();
  return data.manifest;
}

export async function refineShot(params: RefineShotRequest): Promise<{ shot: any; explanation: string }> {
  const res = await fetch('/api/refine-shot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const errMsg = await safeParseError(res, 'Failed to refine shot');
    throw new Error(errMsg);
  }
  return res.json();
}

export async function fetchReferenceStyle(
  videoId: string,
  direction?: string
): Promise<any> {
  const url = direction
    ? `/api/reference-style/${encodeURIComponent(videoId)}?direction=${encodeURIComponent(direction)}`
    : `/api/reference-style/${encodeURIComponent(videoId)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch reference style: ${res.statusText}`);
  const data = await res.json();
  return data.contract;
}

export async function fetchPatterns(): Promise<any> {
  try {
    const res = await fetchWithTimeout('/api/patterns', {}, 2000);
    if (!res.ok) return INSPIRATION_SHORTS;
    const data = await res.json();
    const serverPatterns = data.catalog?.patterns;
    if (Array.isArray(serverPatterns) && serverPatterns.length > 0) {
      return serverPatterns;
    }
    return INSPIRATION_SHORTS;
  } catch {
    return INSPIRATION_SHORTS;
  }
}

export async function fetchPatternExemplars(patternId: string): Promise<any[]> {
  try {
    const res = await fetchWithTimeout(`/api/pattern/${encodeURIComponent(patternId)}/exemplars`, {}, 2000);
    if (!res.ok) return [];
    const data = await res.json();
    return data.exemplars || [];
  } catch {
    return [];
  }
}

export async function fetchInstagramReels(): Promise<any[]> {
  try {
    const res = await fetchWithTimeout('/api/reels', {}, 2000);
    if (!res.ok) return [];
    const data = await res.json();
    return data.reels || [];
  } catch {
    return [];
  }
}


export async function fetchTechniqueLibrary(): Promise<any[]> {
  try {
    const res = await fetchWithTimeout('/api/techniques', {}, 2000);
    if (!res.ok) return [];
    const data = await res.json();
    return data.library?.techniques || [];
  } catch {
    return [];
  }
}

export async function ingestTechniques(): Promise<{ status: string; techniques_count: number; message: string }> {
  const res = await fetch('/api/techniques/ingest', {
    method: 'POST',
  });
  if (!res.ok) {
    const errMsg = await safeParseError(res, 'Failed to ingest techniques from dataset');
    throw new Error(errMsg);
  }
  return res.json();
}

export async function fetchAnalyses(): Promise<any[]> {
  try {
    const res = await fetchWithTimeout('/api/analyses', {}, 2000);
    if (!res.ok) return [];
    const data = await res.json();
    return data.analyses || [];
  } catch {
    return [];
  }
}

export async function fetchAnalysisDetail(videoId: string): Promise<any> {
  const res = await fetch(`/api/analysis/${videoId}`);
  if (!res.ok) {
    const errMsg = await safeParseError(res, `Failed to load analysis detail for ${videoId}`);
    throw new Error(errMsg);
  }
  const data = await res.json();
  return data.analysis;
}

export async function uploadVideoForAnalysis(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/api/analyze-video', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errMsg = await safeParseError(res, 'Failed to analyze uploaded video');
    throw new Error(errMsg);
  }

  const data = await res.json();
  return data.analysis;
}



