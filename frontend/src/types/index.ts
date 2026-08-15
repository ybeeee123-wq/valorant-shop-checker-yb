// Auth types (matching backend models)

export interface SessionResponse {
  valid: boolean;
  puuid?: string;
}

// Store types

export interface SkinOffer {
  uuid: string;
  name: string;
  display_icon: string;
  content_tier_uuid: string;
  content_tier_name: string;
  content_tier_color: string;
  cost: number;
}

export interface BundleItem {
  uuid: string;
  name: string;
  display_icon: string;
  base_price: number;
  discounted_price: number;
  discount_percent: number;
}

export interface Bundle {
  uuid: string;
  name: string;
  display_icon: string | null;
  items: BundleItem[];
  total_base_price: number;
  total_discounted_price: number;
  duration_remaining_secs: number;
}

export interface Wallet {
  valorant_points: number;
  radianite_points: number;
}

export interface DailyStoreResponse {
  offers: SkinOffer[];
  seconds_remaining: number;
}

export interface BundleResponse {
  bundles: Bundle[];
}

export interface NightMarketOffer {
  bonus_offer_id: string;
  offer_id: string;
  uuid: string;
  name: string;
  display_icon: string;
  content_tier_uuid: string;
  content_tier_name: string;
  content_tier_color: string;
  original_cost: number;
  discounted_cost: number;
  discount_percent: number;
  is_seen: boolean;
}

export interface NightMarketResponse {
  active: boolean;
  offers: NightMarketOffer[];
  seconds_remaining: number;
}

export interface SkinCatalogItem {
  uuid: string; name: string; display_icon: string; weapon: string;
  content_tier_uuid: string; content_tier_name: string; content_tier_color: string;
}

export interface SkinPreviewVideo {
  uuid: string;
  name: string;
  ordinal: number;
  streamed_video: string;
  display_icon: string;
  swatch: string;
  level_item: string;
}

export interface SkinPreviewResponse {
  skin_uuid: string;
  name: string;
  display_icon: string;
  levels: SkinPreviewVideo[];
  chromas: SkinPreviewVideo[];
}

export interface WishlistItem {
  skin_uuid: string; skin_name: string; display_icon: string;
  content_tier_name: string; content_tier_color: string; added_at: string;
}

export interface SnapshotOffer {
  skin_uuid: string; skin_name: string; display_icon: string;
  content_tier_name: string; content_tier_color: string; vp_cost: number;
}

export interface HistorySnapshot {
  rotation_key: string; fetched_at: string; seconds_remaining: number; offers: SnapshotOffer[];
}

export interface NotificationPreferences {
  web_push_enabled: boolean; discord_enabled: boolean;
  discord_configured: boolean; email_enabled: boolean; email_configured: boolean;
  notify_only_wishlist_matches: boolean;
}

export interface UserNotification {
  id: string; skin_uuid: string; title: string; body: string;
  display_icon: string; vp_cost: number; target_url: string;
  created_at: string; read_at: string | null;
}

export interface CompanionStatus {
  registered: boolean; online: boolean; device_name: string | null;
  last_seen_at: string | null; last_successful_sync_at: string | null; reauth_required: boolean;
}

// Auth state

export interface AuthState {
  status: 'checking' | 'loading' | 'authenticated' | 'unauthenticated' | 'error';
  sessionValid: boolean;
  puuid: string | null;
  error: string | null;
}

export type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; puuid: string }
  | { type: 'LOGIN_ERROR'; error: string }
  | { type: 'LOGOUT' }
  | { type: 'SESSION_INVALID' }
  | { type: 'SESSION_RESTORED'; puuid: string };
