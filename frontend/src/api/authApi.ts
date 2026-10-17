import { GoogleAuthUrlResponse, UserProfile } from '../types/auth';

export async function fetchGoogleAuthUrl(): Promise<GoogleAuthUrlResponse> {
  const currentRedirect = `${window.location.origin}/oauth-callback`;
  const res = await fetch(`/api/auth/google/url?redirect_uri=${encodeURIComponent(currentRedirect)}`);
  if (!res.ok) {
    throw new Error('Failed to fetch Google auth URL');
  }
  return res.json();
}

export async function sendOAuthCallback(code?: string, demoMode: boolean = false): Promise<UserProfile> {
  const currentRedirect = `${window.location.origin}/oauth-callback`;
  const res = await fetch('/api/auth/google/callback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, demo_mode: demoMode, redirect_uri: currentRedirect }),
  });
  if (!res.ok) {
    throw new Error('Failed to authenticate with Google');
  }
  return res.json();
}

export async function fetchUserProfile(): Promise<UserProfile> {
  const res = await fetch('/api/user/profile');
  if (!res.ok) {
    throw new Error('Failed to fetch user profile');
  }
  return res.json();
}

export async function syncCreatorDNA(): Promise<UserProfile> {
  const res = await fetch('/api/user/sync-dna', {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error('Failed to synchronize Creator DNA');
  }
  return res.json();
}

export async function logoutUser(): Promise<void> {
  await fetch('/api/auth/logout', {
    method: 'POST',
  });
}

