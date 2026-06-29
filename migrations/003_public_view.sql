-- Public-facing view: deliberately OMITS reporter_telegram_id. Only published rows.
-- SECURITY INVOKER ensures RLS on the base table is respected.
create or replace view public_problems with (security_invoker=true) as
select
  id, created_at, reporter_handle, media_type, media_url,
  title, description, category, legality_bin, severity,
  latitude, longitude, status, upvotes,
  coalesce(stage, 'heard') as stage,
  gov_status, gov_days, is_sensitive
from problems
where status = 'published';

-- Defense in depth: enable RLS on the base table.
alter table problems enable row level security;

-- Grant column-level SELECT on safe columns only (reporter_telegram_id stays locked).
grant select (id, created_at, reporter_handle, media_type, media_url,
              title, description, category, legality_bin, severity,
              latitude, longitude, status, upvotes,
              stage, gov_status, gov_days, is_sensitive) on problems to anon;

-- RLS policy lets anon see only published rows.
drop policy if exists anon_select_published on problems;
create policy anon_select_published on problems
  for select to anon
  using (status = 'published');

-- Expose ONLY the safe view to the public (anon) role.
grant select on public_problems to anon;
