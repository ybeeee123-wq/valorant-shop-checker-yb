create table if not exists web_sessions (
  id text primary key default gen_random_uuid()::text,
  user_id text not null references users(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  revoked boolean not null default false,
  created_at timestamptz not null default now(),
  last_seen_at timestamptz
);

create table if not exists storefront_states (
  user_id text primary key references users(id) on delete cascade,
  rotation_key text not null,
  seconds_remaining integer not null default 0,
  offers_json text not null default '[]',
  bundles_json text not null default '[]',
  night_market_json text not null default '{"active":false,"offers":[],"seconds_remaining":0}',
  wallet_json text not null default '{"valorant_points":0,"radianite_points":0}',
  synced_at timestamptz not null default now()
);

create index if not exists idx_web_sessions_user on web_sessions(user_id);
create index if not exists idx_web_sessions_expiry on web_sessions(expires_at);
create index if not exists idx_pairing_user on companion_pairing_challenges(user_id);
create index if not exists idx_snapshot_items_snapshot on shop_snapshot_items(snapshot_id);

alter table web_sessions enable row level security;
alter table storefront_states enable row level security;

revoke all on table web_sessions from anon, authenticated;
revoke all on table storefront_states from anon, authenticated;
