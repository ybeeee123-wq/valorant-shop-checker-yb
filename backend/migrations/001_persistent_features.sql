create extension if not exists pgcrypto;

create table if not exists users (
  id text primary key default gen_random_uuid()::text, puuid text not null unique,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists wishlist_items (
  id text primary key default gen_random_uuid()::text, user_id text not null references users(id) on delete cascade,
  skin_uuid text not null, skin_name text not null, display_icon text not null default '',
  content_tier_name text not null default 'Unknown', content_tier_color text not null default '',
  added_at timestamptz not null default now(), unique(user_id, skin_uuid)
);
create table if not exists shop_snapshots (
  id text primary key default gen_random_uuid()::text, user_id text not null references users(id) on delete cascade,
  rotation_key text not null, fetched_at timestamptz not null default now(),
  seconds_remaining integer not null default 0, raw_offer_count integer not null default 0,
  unique(user_id, rotation_key)
);
create table if not exists shop_snapshot_items (
  id text primary key default gen_random_uuid()::text, snapshot_id text not null references shop_snapshots(id) on delete cascade,
  skin_uuid text not null, skin_name text not null, display_icon text not null default '',
  content_tier_name text not null default 'Unknown', content_tier_color text not null default '', vp_cost integer not null
);
create table if not exists notification_preferences (
  user_id text primary key references users(id) on delete cascade,
  web_push_enabled boolean not null default false, discord_enabled boolean not null default false,
  discord_webhook_encrypted text, notify_only_wishlist_matches boolean not null default true,
  updated_at timestamptz not null default now()
);
create table if not exists push_subscriptions (
  id text primary key default gen_random_uuid()::text, user_id text not null references users(id) on delete cascade,
  endpoint text not null, p256dh text not null, auth text not null,
  created_at timestamptz not null default now(), last_used_at timestamptz,
  unique(user_id, endpoint)
);
create table if not exists companion_devices (
  id text primary key default gen_random_uuid()::text, user_id text not null references users(id) on delete cascade,
  device_name text not null, device_token_hash text not null unique, last_seen_at timestamptz,
  last_successful_sync_at timestamptz, reauth_required boolean not null default false,
  revoked boolean not null default false, created_at timestamptz not null default now()
);
create table if not exists notification_events (
  id text primary key default gen_random_uuid()::text, user_id text not null references users(id) on delete cascade,
  skin_uuid text not null, rotation_key text not null, channel text not null,
  status text not null default 'pending', error text, sent_at timestamptz,
  unique(user_id, skin_uuid, rotation_key, channel)
);
create table if not exists companion_pairing_challenges (
  id text primary key default gen_random_uuid()::text,
  challenge_hash text not null unique, verifier_hash text not null, device_name text not null,
  user_id text references users(id) on delete cascade, device_token_encrypted text,
  expires_at timestamptz not null, completed_at timestamptz, used_at timestamptz,
  poll_attempts integer not null default 0, created_at timestamptz not null default now()
);

create index if not exists idx_wishlist_user on wishlist_items(user_id);
create index if not exists idx_snapshots_user on shop_snapshots(user_id);
create index if not exists idx_devices_user on companion_devices(user_id);
create index if not exists idx_pairing_challenge on companion_pairing_challenges(challenge_hash);
