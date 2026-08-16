document.getElementById("year").textContent = new Date().getFullYear();

const themeToggle = document.getElementById("themeToggle");
const root = document.documentElement;
const savedTheme = localStorage.getItem("theme");

if (savedTheme) {
  root.setAttribute("data-theme", savedTheme);
  themeToggle.textContent = savedTheme === "dark" ? "☀️" : "🌙";
}

themeToggle.addEventListener("click", () => {
  const isDark = root.getAttribute("data-theme") === "dark";
  const next = isDark ? "light" : "dark";
  root.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
  themeToggle.textContent = isDark ? "🌙" : "☀️";
});

// Publishable key only — safe to expose in client-side code.
// Never put the Supabase secret key here; RLS policies restrict what this key can do.
const SUPABASE_URL = "https://wxaehswbzymtaeggxubm.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_ED5lSv3N8zdKUzRF-Arn0w_R3ALO5_J";
const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);

let currentUser = null;
let posts = [];

function escapeHtml(text) {
  return text.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

const IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "webp", "svg"];

function isImageFile(name) {
  const ext = name.split(".").pop().toLowerCase();
  return IMAGE_EXTENSIONS.includes(ext);
}

// --- View switching ---
// The header stays fixed; only the <main> content swaps between these views.

const views = {
  home: document.getElementById("viewHome"),
  post: document.getElementById("viewPost"),
  login: document.getElementById("viewLogin"),
  recovery: document.getElementById("viewRecovery"),
  recoveryComplete: document.getElementById("viewRecoveryComplete"),
  write: document.getElementById("viewWrite"),
};

function showView(name) {
  Object.values(views).forEach((el) => {
    el.hidden = true;
  });
  views[name].hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// --- Posts (public read, owner-only write) ---

const postList = document.getElementById("postList");
const postDetail = document.getElementById("postDetail");
const backToListBtn = document.getElementById("backToListBtn");

async function loadPosts() {
  const { data, error } = await supabaseClient
    .from("posts")
    .select("id, title, content, created_at, attachment_url, attachment_name")
    .order("created_at", { ascending: false });

  if (error) {
    postList.innerHTML = '<p class="post-list__empty">글을 불러오지 못했습니다.</p>';
    return;
  }

  posts = data || [];

  if (posts.length === 0) {
    postList.innerHTML = '<p class="post-list__empty">아직 기록된 시도가 없습니다.</p>';
    return;
  }

  postList.innerHTML = posts
    .map((post) => {
      const date = new Date(post.created_at).toLocaleDateString("ko-KR");
      return `
        <button type="button" class="post-card" data-id="${post.id}">
          <div class="post-card__date">${date}</div>
          <h3 class="post-card__title">${escapeHtml(post.title)}</h3>
          <p class="post-card__excerpt">${escapeHtml(post.content)}</p>
        </button>
      `;
    })
    .join("");

  postList.querySelectorAll(".post-card").forEach((card) => {
    card.addEventListener("click", () => openPost(card.dataset.id));
  });
}

function renderAttachment(post) {
  if (!post.attachment_url) return "";

  if (isImageFile(post.attachment_name || post.attachment_url)) {
    return `
      <div class="post-detail__attachment">
        <img src="${post.attachment_url}" alt="${escapeHtml(post.attachment_name || "첨부 이미지")}" />
      </div>
    `;
  }

  return `
    <div class="post-detail__attachment">
      <a class="post-detail__attachment-link" href="${post.attachment_url}" target="_blank" rel="noopener noreferrer">
        📎 ${escapeHtml(post.attachment_name || "첨부파일 열기")}
      </a>
    </div>
  `;
}

function openPost(id) {
  const post = posts.find((p) => p.id === id);
  if (!post) return;

  const date = new Date(post.created_at).toLocaleDateString("ko-KR");
  postDetail.innerHTML = `
    <div class="post-detail__date">${date}</div>
    <h2 class="post-detail__title">${escapeHtml(post.title)}</h2>
    <div class="post-detail__content">${escapeHtml(post.content)}</div>
    ${renderAttachment(post)}
  `;
  showView("post");
}

backToListBtn.addEventListener("click", () => showView("home"));

// --- Nav auth controls ---

const navLoggedOut = document.getElementById("navLoggedOut");
const navLoggedIn = document.getElementById("navLoggedIn");
const navLoginBtn = document.getElementById("navLoginBtn");
const navWriteBtn = document.getElementById("navWriteBtn");
const navLogoutBtn = document.getElementById("navLogoutBtn");

navLoginBtn.addEventListener("click", () => showView("login"));
navWriteBtn.addEventListener("click", () => showView("write"));

navLogoutBtn.addEventListener("click", async () => {
  await supabaseClient.auth.signOut();
  showView("home");
});

function updateAuthUI(user) {
  currentUser = user;

  if (user) {
    navLoggedOut.hidden = true;
    navLoggedIn.hidden = false;
  } else {
    navLoggedOut.hidden = false;
    navLoggedIn.hidden = true;
  }
}

// --- Login ---

const authForm = document.getElementById("authForm");
const authStatus = document.getElementById("authStatus");
const forgotPasswordBtn = document.getElementById("forgotPasswordBtn");

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authStatus.textContent = "";
  authStatus.className = "form-status";

  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;

  const { error } = await supabaseClient.auth.signInWithPassword({ email, password });

  if (error) {
    authStatus.textContent = "로그인에 실패했습니다: " + error.message;
    authStatus.classList.add("form-status--error");
    return;
  }

  authForm.reset();
  showView("home");
});

forgotPasswordBtn.addEventListener("click", async () => {
  authStatus.textContent = "";
  authStatus.className = "form-status";

  const email = document.getElementById("authEmail").value.trim();

  if (!email) {
    authStatus.textContent = "재설정 링크를 받을 이메일을 먼저 입력해 주세요.";
    authStatus.classList.add("form-status--error");
    return;
  }

  const { error } = await supabaseClient.auth.resetPasswordForEmail(email, {
    redirectTo: window.location.href.split("#")[0].split("?")[0],
  });

  if (error) {
    authStatus.textContent = "재설정 이메일 발송에 실패했습니다: " + error.message;
    authStatus.classList.add("form-status--error");
    return;
  }

  authStatus.textContent = "비밀번호 재설정 링크를 이메일로 보냈습니다.";
  authStatus.classList.add("form-status--success");
});

// --- Password recovery ---

const recoveryForm = document.getElementById("recoveryForm");
const recoveryStatus = document.getElementById("recoveryStatus");
const goToLoginBtn = document.getElementById("goToLoginBtn");

recoveryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  recoveryStatus.textContent = "";
  recoveryStatus.className = "form-status";

  const newPassword = document.getElementById("newPassword").value;
  const { error } = await supabaseClient.auth.updateUser({ password: newPassword });

  if (error) {
    recoveryStatus.textContent = "변경에 실패했습니다: " + error.message;
    recoveryStatus.classList.add("form-status--error");
    return;
  }

  recoveryForm.reset();
  await supabaseClient.auth.signOut();
  showView("recoveryComplete");
});

goToLoginBtn.addEventListener("click", () => showView("login"));

// --- Write a post ---

const postForm = document.getElementById("postForm");
const postStatus = document.getElementById("postStatus");

postForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  postStatus.textContent = "";
  postStatus.className = "form-status";

  const submitBtn = postForm.querySelector("button[type='submit']");
  submitBtn.disabled = true;

  let attachmentUrl = null;
  let attachmentName = null;

  const file = document.getElementById("postFile").files[0];

  if (file) {
    const path = `${Date.now()}-${file.name}`;
    const { error: uploadError } = await supabaseClient.storage.from("post-files").upload(path, file);

    if (uploadError) {
      submitBtn.disabled = false;
      postStatus.textContent = "파일 업로드에 실패했습니다: " + uploadError.message;
      postStatus.classList.add("form-status--error");
      return;
    }

    attachmentUrl = supabaseClient.storage.from("post-files").getPublicUrl(path).data.publicUrl;
    attachmentName = file.name;
  }

  const { error } = await supabaseClient.from("posts").insert({
    title: document.getElementById("postTitle").value.trim(),
    content: document.getElementById("postContent").value.trim(),
    attachment_url: attachmentUrl,
    attachment_name: attachmentName,
  });

  submitBtn.disabled = false;

  if (error) {
    postStatus.textContent = "게시에 실패했습니다: " + error.message;
    postStatus.classList.add("form-status--error");
    return;
  }

  postForm.reset();
  await loadPosts();
  showView("home");
});

// --- Auth session wiring ---

supabaseClient.auth.onAuthStateChange((event, session) => {
  if (event === "PASSWORD_RECOVERY") {
    showView("recovery");
    return;
  }
  updateAuthUI(session ? session.user : null);
});

supabaseClient.auth.getSession().then(({ data }) => {
  updateAuthUI(data.session ? data.session.user : null);
});

loadPosts();
