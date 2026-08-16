-- Run this in the Supabase SQL Editor.
create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  content text not null,
  created_at timestamptz not null default now()
);

alter table public.posts enable row level security;

-- Anyone visiting the blog can read posts.
create policy "Public can read posts" on public.posts
  for select
  to anon, authenticated
  using (true);

-- Only a logged-in account can create posts. There is no public sign-up
-- form on the site, so in practice this means only the site owner.
create policy "Authenticated can write posts" on public.posts
  for insert
  to authenticated
  with check (true);
