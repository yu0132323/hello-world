-- Run this in the Supabase SQL Editor.

-- Public bucket to hold files attached to posts (images, zips, html demos, etc.)
insert into storage.buckets (id, name, public)
values ('post-files', 'post-files', true)
on conflict (id) do nothing;

-- Anyone can view/download files in this bucket.
create policy "Public can read post files" on storage.objects
  for select
  to public
  using (bucket_id = 'post-files');

-- Only a logged-in account (the site owner, since there's no public sign-up) can upload.
create policy "Authenticated can upload post files" on storage.objects
  for insert
  to authenticated
  with check (bucket_id = 'post-files');

-- Let posts reference an uploaded file.
alter table public.posts
  add column if not exists attachment_url text,
  add column if not exists attachment_name text;
