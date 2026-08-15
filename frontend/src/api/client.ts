import type {
  BundleResponse,
  DailyStoreResponse,
  NightMarketResponse,
  SkinCatalogItem,
  SkinPreviewResponse,
  WishlistItem,
  HistorySnapshot,
  NotificationPreferences,
  UserNotification,
  CompanionStatus,
  SessionResponse,
  Wallet,
} from '../types';
import { STORE_CACHE_KEY } from '../utils/storeCache';

const BASE_URL = import.meta.env.VITE_API_URL ?? '';
const TOKEN_KEY = 'session_token';
const previewCache = new Map<string, SkinPreviewResponse>();
const previewRequests = new Map<string, Promise<SkinPreviewResponse>>();

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function isAuthenticationError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  sessionStorage.removeItem(STORE_CACHE_KEY);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(STORE_CACHE_KEY);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (options?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');

  const token = getStoredToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new ApiError(body.detail ?? `Request failed: ${res.status}`, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
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

export function getSkins(q = '', weapon = '', signal?: AbortSignal): Promise<SkinCatalogItem[]> {
  return request(`/api/skins?q=${encodeURIComponent(q)}&weapon=${encodeURIComponent(weapon)}&limit=100`, { signal });
}

export function getSkinPreview(skinUuid: string): Promise<SkinPreviewResponse> {
  const key = skinUuid.toLowerCase();
  const cached = previewCache.get(key);
  if (cached) return Promise.resolve(cached);
  const pending = previewRequests.get(key);
  if (pending) return pending;
  const requestPromise = request<SkinPreviewResponse>(`/api/skins/${encodeURIComponent(key)}/preview`)
    .then((preview) => {
      previewCache.set(key, preview);
      previewCache.set(preview.skin_uuid.toLowerCase(), preview);
      return preview;
    })
    .finally(() => previewRequests.delete(key));
  previewRequests.set(key, requestPromise);
  return requestPromise;
}

export function preloadSkinPreview(skinUuid: string): void {
  void getSkinPreview(skinUuid).catch(() => undefined);
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
export function testNotification(channel: 'web_push' | 'discord' | 'email'): Promise<{ status: string }> {
  return request('/api/notifications/test', { method: 'POST', body: JSON.stringify({ channel }) });
}
export function getNotifications(): Promise<UserNotification[]> { return request('/api/notifications'); }
export function readNotification(id: string): Promise<void> {
  return request(`/api/notifications/${encodeURIComponent(id)}/read`, { method: 'POST' });
}
export function readAllNotifications(): Promise<void> {
  return request('/api/notifications/read-all', { method: 'POST' });
}
export function getCompanionStatus(): Promise<CompanionStatus> { return request('/api/companion/status'); }
export function revokeCompanion(): Promise<void> { return request('/api/companion/device', { method: 'DELETE' }); }
export function getPairingStatus(challenge: string): Promise<{ status: string; device_name?: string | null }> {
  return request(`/api/companion/pairing/status?challenge=${encodeURIComponent(challenge)}`);
}
export function approvePairing(challenge: string): Promise<{ status: string; device_name?: string | null }> {
  return request('/api/companion/pairing/approve', { method: 'POST', body: JSON.stringify({ challenge }) });
}
