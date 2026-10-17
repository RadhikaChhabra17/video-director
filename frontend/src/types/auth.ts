export interface CreatorDNA {
  pacing_baseline_cuts_per_10s: number;
  signature_framing: string;
  vocal_cadence_wpm: number;
  audio_energy_profile: string;
  signature_hook_type: string;
  color_palette: string;
  retention_benchmark: number;
}

export interface YouTubeShortItem {
  video_id: string;
  title: string;
  views: number;
  retention_rate: number;
  duration_sec: number;
  published_date: string;
  top_hook: string;
}

export interface UserProfile {
  authenticated: boolean;
  email?: string;
  name?: string;
  picture?: string;
  channel_title?: string;
  channel_handle?: string;
  subscribers_count?: number;
  total_views?: number;
  shorts_count?: number;
  creator_dna?: CreatorDNA;
  top_shorts?: YouTubeShortItem[];
}

export interface GoogleAuthUrlResponse {
  auth_url: string;
  is_configured: boolean;
  client_id?: string;
}

