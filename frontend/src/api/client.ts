import type {
  BundleResponse,
  DailyStoreResponse,
  NightMarketResponse,
  SkinCatalogItem,
  WishlistItem,
  HistorySnapshot,
  NotificationPreferences,
  CompanionStatus,
  SessionResponse,
  Wallet,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL ?? '';
const TOKEN_KEY = 'session_token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const token = getStoredToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

// Auth

export interface LoginResponse {
  status: 'success' | 'error';
  session_token?: string | null;
  puuid?: string | null;
  error?: string | null;
}

export function getAuthUrl(): Promise<{ auth_url: string }> {
  return request('/api/auth/url');
}

export function submitToken(url: string): Promise<LoginResponse> {
  return request('/api/auth/token', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}

export function logout(): Promise<{ status: string }> {
  return request('/api/auth/logout', { method: 'POST' });
}

export function checkSession(): Promise<SessionResponse> {
  return request('/api/auth/session');
}

// Store

export function getDailyStore(): Promise<DailyStoreResponse> {
  return request('/api/store/daily');
}

export function getBundles(): Promise<BundleResponse> {
  return request('/api/store/bundle');
}

export function getWallet(): Promise<Wallet> {
  return request('/api/store/wallet');
}

export function getNightMarket(): Promise<NightMarketResponse> {
  return request('/api/store/night-market');
}

export function getSkins(q = '', weapon = ''): Promise<SkinCatalogItem[]> {
  return request(`/api/skins?q=${encodeURIComponent(q)}&weapon=${encodeURIComponent(weapon)}&limit=100`);
}

export function getWishlist(): Promise<WishlistItem[]> { return request('/api/wishlist'); }
export function addWishlist(skin_uuid: string): Promise<WishlistItem> {
  return request('/api/wishlist', { method: 'POST', body: JSON.stringify({ skin_uuid }) });
}
export function removeWishlist(skinUuid: string): Promise<void> {
  return request(`/api/wishlist/${encodeURIComponent(skinUuid)}`, { method: 'DELETE' });
}
export function getHistory(): Promise<HistorySnapshot[]> { return request('/api/history'); }
export function getNotificationPreferences(): Promise<NotificationPreferences> { return request('/api/notifications/preferences'); }
export function updateNotificationPreferences(body: Record<string, unknown>): Promise<NotificationPreferences> {
  return request('/api/notifications/preferences', { method: 'PUT', body: JSON.stringify(body) });
}
export function getVapidPublicKey(): Promise<{ public_key: string }> { return request('/api/notifications/vapid-public-key'); }
export function subscribePush(subscription: PushSubscriptionJSON): Promise<void> {
  return request('/api/notifications/push/subscribe', {
    method: 'POST',
    body: JSON.stringify({ endpoint: subscription.endpoint, p256dh: subscription.keys?.p256dh, auth: subscription.keys?.auth }),
  });
}
export function unsubscribePush(endpoint: string): Promise<void> {
  return request('/api/notifications/push/subscribe', { method: 'DELETE', body: JSON.stringify({ endpoint }) });
}
export function testNotification(channel: 'web_push' | 'discord'): Promise<{ status: string }> {
  return request('/api/notifications/test', { method: 'POST', body: JSON.stringify({ channel }) });
}
export function getCompanionStatus(): Promise<CompanionStatus> { return request('/api/companion/status'); }
export function revokeCompanion(): Promise<void> { return request('/api/companion/device', { method: 'DELETE' }); }
export function getPairingStatus(challenge: string): Promise<{ status: string; device_name?: string | null }> {
  return request(`/api/companion/pairing/status?challenge=${encodeURIComponent(challenge)}`);
}
export function approvePairing(challenge: string): Promise<{ status: string; device_name?: string | null }> {
  return request('/api/companion/pairing/approve', { method: 'POST', body: JSON.stringify({ challenge }) });
}
