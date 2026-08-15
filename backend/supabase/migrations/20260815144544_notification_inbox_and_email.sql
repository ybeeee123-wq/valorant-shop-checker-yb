create table if not exists user_notifications (
  id text primary key default gen_random_uuid()::text,
  user_id text not null references users(id) on delete cascade,
  skin_uuid text not null,
  rotation_key text not null,
  title text not null,
  body text not null,
  display_icon text not null default '',
  vp_cost integer not null,
  target_url text not null default '/shop',
  created_at timestamptz not null default now(),
  read_at timestamptz,
  unique(user_id, skin_uuid, rotation_key)
);

create table if not exists notification_contacts (
  user_id text primary key references users(id) on delete cascade,
  email_enabled boolean not null default false,
  email_encrypted text,
  updated_at timestamptz not null default now()
);

create index if not exists idx_user_notifications_user_created
  on user_notifications(user_id, created_at desc);
create index if not exists idx_user_notifications_unread
  on user_notifications(user_id, read_at) where read_at is null;

alter table user_notifications enable row level security;
alter table notification_contacts enable row level security;

revoke all on table user_notifications from anon, authenticated;
revoke all on table notification_contacts from anon, authenticated;
