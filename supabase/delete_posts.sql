-- Run this in the Supabase SQL Editor.

-- Only a logged-in account (the site owner) can delete posts.
create policy "Authenticated can delete posts" on public.posts
  for delete
  to authenticated
  using (true);
