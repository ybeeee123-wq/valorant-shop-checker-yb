import type { BundleResponse, DailyStoreResponse, NightMarketResponse, Wallet } from '../types';

export const STORE_CACHE_KEY = 'valshop-storefront-v1';

interface StoreCache {
  storedAt: number;
  daily?: DailyStoreResponse;
  bundles?: BundleResponse;
  wallet?: Wallet;
  nightMarket?: NightMarketResponse;
}

function readRaw(): StoreCache | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(STORE_CACHE_KEY) ?? 'null') as StoreCache | null;
    return value && value.storedAt > 0 ? value : null;
  } catch {
    sessionStorage.removeItem(STORE_CACHE_KEY);
    return null;
  }
}

export function readStoreCache(): StoreCache | null {
  const cached = readRaw();
  if (!cached || Date.now() - cached.storedAt > 6 * 60 * 60 * 1000) return null;
  const elapsed = Math.max(0, Math.floor((Date.now() - cached.storedAt) / 1000));
  const daily = cached.daily && cached.daily.seconds_remaining > elapsed
    ? { ...cached.daily, seconds_remaining: cached.daily.seconds_remaining - elapsed }
    : undefined;
  const nightMarket = cached.nightMarket
    ? { ...cached.nightMarket, seconds_remaining: Math.max(0, cached.nightMarket.seconds_remaining - elapsed) }
    : undefined;
  return { ...cached, daily, nightMarket };
}

export function updateStoreCache(update: Omit<Partial<StoreCache>, 'storedAt'>): void {
  try {
    const current = readStoreCache() ?? { storedAt: Date.now() };
    sessionStorage.setItem(STORE_CACHE_KEY, JSON.stringify({ ...current, ...update, storedAt: Date.now() }));
  } catch {
    // Storage can be unavailable in hardened/private browser modes.
  }
}
