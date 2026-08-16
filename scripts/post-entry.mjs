// Posts one blog entry to the "posts" table.
// Usage: BLOG_OWNER_EMAIL=... BLOG_OWNER_PASSWORD=... node scripts/post-entry.mjs "제목" "내용"
// Run this locally (not from a sandboxed/remote session) since it needs real internet access.

const SUPABASE_URL = "https://wxaehswbzymtaeggxubm.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_ED5lSv3N8zdKUzRF-Arn0w_R3ALO5_J";

const [title, content] = process.argv.slice(2);
const email = process.env.BLOG_OWNER_EMAIL;
const password = process.env.BLOG_OWNER_PASSWORD;

if (!title || !content) {
  console.error('Usage: node scripts/post-entry.mjs "제목" "내용"');
  process.exit(1);
}

if (!email || !password) {
  console.error("Set BLOG_OWNER_EMAIL and BLOG_OWNER_PASSWORD environment variables first.");
  process.exit(1);
}

const tokenRes = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
  method: "POST",
  headers: {
    apikey: SUPABASE_PUBLISHABLE_KEY,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ email, password }),
});

const tokenData = await tokenRes.json();

if (!tokenRes.ok) {
  console.error("로그인 실패:", tokenData.error_description || tokenData.msg || tokenRes.status);
  process.exit(1);
}

const postRes = await fetch(`${SUPABASE_URL}/rest/v1/posts`, {
  method: "POST",
  headers: {
    apikey: SUPABASE_PUBLISHABLE_KEY,
    Authorization: `Bearer ${tokenData.access_token}`,
    "Content-Type": "application/json",
    Prefer: "return=minimal",
  },
  body: JSON.stringify({ title, content }),
});

if (!postRes.ok) {
  const err = await postRes.text();
  console.error("게시 실패:", err);
  process.exit(1);
}

console.log("게시 완료:", title);
