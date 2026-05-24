-- Voice Debrief beta schema (3-user private beta)

create extension if not exists pgcrypto;

create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  created_at timestamptz not null default now()
);

create table if not exists user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  voice_name text not null default 'en-US-AriaNeural',
  endpoint_min_speech_seconds real not null default 0.55,
  endpoint_min_text_chars int not null default 8,
  vad_silence_ms int not null default 700,
  setup_complete boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists debrief_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  title text,
  summary_markdown text
);

create table if not exists debrief_turns (
  id bigserial primary key,
  session_id uuid not null references debrief_sessions(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  speaker text not null,
  text text not null,
  created_at timestamptz not null default now()
);

create table if not exists usage_monthly (
  id bigserial primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  month_key text not null,
  stt_minutes numeric(10,2) not null default 0,
  est_cost_usd numeric(10,2) not null default 0,
  unique (user_id, month_key)
);

create index if not exists idx_debrief_sessions_user_id on debrief_sessions(user_id);
create index if not exists idx_debrief_turns_user_id on debrief_turns(user_id);
create index if not exists idx_debrief_turns_session_id on debrief_turns(session_id);
