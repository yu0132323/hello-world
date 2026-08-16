// Posts one blog entry to the "posts" table, optionally attaching a file.
// Usage: BLOG_OWNER_EMAIL=... BLOG_OWNER_PASSWORD=... node scripts/post-entry.mjs "제목" "내용" [파일경로]
// Run this locally (not from a sandboxed/remote session) since it needs real internet access.

import { readFileSync } from "node:fs";
import { basename, extname } from "node:path";

const SUPABASE_URL = "https://wxaehswbzymtaeggxubm.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_ED5lSv3N8zdKUzRF-Arn0w_R3ALO5_J";

const MIME_TYPES = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".pdf": "application/pdf",
  ".zip": "application/zip",
  ".html": "text/html",
  ".htm": "text/html",
  ".txt": "text/plain",
};

const [title, content, filePath] = process.argv.slice(2);
const email = process.env.BLOG_OWNER_EMAIL;
const password = process.env.BLOG_OWNER_PASSWORD;

if (!title || !content) {
  console.error('Usage: node scripts/post-entry.mjs "제목" "내용" [파일경로]');
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

const accessToken = tokenData.access_token;

let attachmentUrl = null;
let attachmentName = null;

if (filePath) {
  let fileData;
  try {
    fileData = readFileSync(filePath);
  } catch (err) {
    console.error("파일을 읽을 수 없습니다:", err.message);
    process.exit(1);
  }

  attachmentName = basename(filePath);
  const storagePath = `${Date.now()}-${attachmentName}`;
  const contentType = MIME_TYPES[extname(attachmentName).toLowerCase()] || "application/octet-stream";

  const uploadRes = await fetch(`${SUPABASE_URL}/storage/v1/object/post-files/${storagePath}`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_PUBLISHABLE_KEY,
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": contentType,
    },
    body: fileData,
  });

  if (!uploadRes.ok) {
    const err = await uploadRes.text();
    console.error("파일 업로드 실패:", err);
    process.exit(1);
  }

  attachmentUrl = `${SUPABASE_URL}/storage/v1/object/public/post-files/${storagePath}`;
}

const postRes = await fetch(`${SUPABASE_URL}/rest/v1/posts`, {
  method: "POST",
  headers: {
    apikey: SUPABASE_PUBLISHABLE_KEY,
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
    Prefer: "return=minimal",
  },
  body: JSON.stringify({
    title,
    content,
    attachment_url: attachmentUrl,
    attachment_name: attachmentName,
  }),
});

if (!postRes.ok) {
  const err = await postRes.text();
  console.error("게시 실패:", err);
  process.exit(1);
}

console.log("게시 완료:", title, attachmentName ? `(첨부: ${attachmentName})` : "");
