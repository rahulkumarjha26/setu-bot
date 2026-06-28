-- migrations/001_init.sql
create extension if not exists "pgcrypto";

create table if not exists problems (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  reporter_telegram_id bigint,          -- PRIVATE, never exposed publicly
  reporter_handle text,                 -- public pseudonym e.g. Citizen#4821
  media_type text,                      -- 'audio' | 'video' | 'photo'
  media_url text,
  transcript text,
  detected_language text,
  title text,
  description text,
  category text,
  legality_bin text,                    -- 'fundable' | 'statutory' | 'reframe'
  severity text,                        -- 'low' | 'medium' | 'high'
  latitude double precision,
  longitude double precision,
  consent_public boolean default false,
  consent_contact boolean default false,
  status text default 'pending_review', -- 'pending_review' | 'published' | 'rejected'
  upvotes integer default 0
);

-- index for the public map to read published rows fast
create index if not exists idx_problems_status on problems(status);
