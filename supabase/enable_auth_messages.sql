-- Run this in the Supabase SQL Editor after contact_messages.sql has already been applied.

alter table public.contact_messages
  add column if not exists user_id uuid references auth.users(id);

drop policy if exists "Allow public insert" on public.contact_messages;

-- Anyone can still submit without an account (user_id stays null),
-- but a logged-in user can only attach messages to their own account.
create policy "Allow insert own or anonymous" on public.contact_messages
  for insert
  to anon, authenticated
  with check (
    (auth.uid() is not null and user_id = auth.uid())
    or (auth.uid() is null and user_id is null)
  );

-- Logged-in users can read back only the messages tied to their own account.
create policy "Allow read own messages" on public.contact_messages
  for select
  to authenticated
  using (auth.uid() = user_id);
