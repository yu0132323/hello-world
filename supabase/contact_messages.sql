-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor) once.
create table if not exists public.contact_messages (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  message text not null,
  created_at timestamptz not null default now()
);

alter table public.contact_messages enable row level security;

-- Allow the public (anon/publishable key) to submit messages, but not read them back.
create policy "Allow public insert" on public.contact_messages
  for insert
  to anon
  with check (true);
