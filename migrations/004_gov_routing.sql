-- honest sub-states for statutory wounds
alter table problems add column if not exists gov_authority text;   -- 'MCD' | 'DJB' | null
alter table problems add column if not exists gov_filed text default 'awaiting_citizen';
-- gov_filed ∈ 'awaiting_citizen' | 'filed_by_citizen' | 'acknowledged' | 'resolved'

-- expose the new fields in the public view (drop + recreate due to column ordering)
drop view if exists public_problems;
create or replace view public_problems with (security_invoker=true) as
select id, created_at, reporter_handle, media_type, media_url,
  title, description, category, legality_bin, severity,
  latitude, longitude, status, upvotes,
  coalesce(stage,'heard') as stage, gov_status, gov_days,
  gov_authority, gov_filed, is_sensitive
from problems
where status = 'published';

-- Update column-level grant to include new fields
revoke select on problems from anon;
grant select (id, created_at, reporter_handle, media_type, media_url,
              title, description, category, legality_bin, severity,
              latitude, longitude, status, upvotes,
              stage, gov_status, gov_days,
              gov_authority, gov_filed, is_sensitive) on problems to anon;

grant select on public_problems to anon;
