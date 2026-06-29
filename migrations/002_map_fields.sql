-- Adds map/lifecycle fields. Safe to run multiple times.
alter table problems add column if not exists stage text default 'heard';
-- stage ∈ 'heard' | 'sorted' | 'funded' | 'built' | 'proven'
alter table problems add column if not exists gov_status text;
-- gov_status (for statutory wounds) ∈ null | 'routed' | 'pending' | 'no_action' | 'resolved'
alter table problems add column if not exists gov_days integer default 0;
-- days since routed to government, for honest "47 days, no action" labels
alter table problems add column if not exists is_sensitive boolean default false;
-- true = person-related wound; map will fuzz the exact location
