-- Run this in the Supabase SQL editor:
-- https://supabase.com/dashboard/project/ykfjnageewaonunrnwft/sql

-- Idempotent anon read policies for dashboard (Phase 2)
drop policy if exists "anon read" on skills;
drop policy if exists "anon read" on runs;
drop policy if exists "anon read" on plans;
drop policy if exists "anon read" on wiki_articles;

create policy "anon read" on skills        for select using (true);
create policy "anon read" on runs          for select using (true);
create policy "anon read" on plans         for select using (true);
create policy "anon read" on wiki_articles for select using (true);
