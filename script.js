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

const contactForm = document.getElementById("contactForm");
const formStatus = document.getElementById("formStatus");

let currentUser = null;

contactForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  formStatus.textContent = "";
  formStatus.className = "form-status";

  const submitBtn = contactForm.querySelector("button[type='submit']");
  submitBtn.disabled = true;

  const { error } = await supabaseClient.from("contact_messages").insert({
    name: document.getElementById("name").value.trim(),
    email: document.getElementById("email").value.trim(),
    message: document.getElementById("message").value.trim(),
    user_id: currentUser ? currentUser.id : null,
  });

  submitBtn.disabled = false;

  if (error) {
    formStatus.textContent = "전송에 실패했습니다. 잠시 후 다시 시도해 주세요.";
    formStatus.classList.add("form-status--error");
    return;
  }

  formStatus.textContent = "메시지가 전송되었습니다. 감사합니다!";
  formStatus.classList.add("form-status--success");
  contactForm.reset();

  if (currentUser) {
    loadMyMessages();
  }
});

// --- Login / signup ---

const authForm = document.getElementById("authForm");
const authStatus = document.getElementById("authStatus");
const signupBtn = document.getElementById("signupBtn");
const logoutBtn = document.getElementById("logoutBtn");
const authLoggedOut = document.getElementById("authLoggedOut");
const authLoggedIn = document.getElementById("authLoggedIn");
const userEmailDisplay = document.getElementById("userEmailDisplay");
const myMessagesList = document.getElementById("myMessages");

function updateAuthUI(user) {
  currentUser = user;

  if (user) {
    authLoggedOut.hidden = true;
    authLoggedIn.hidden = false;
    userEmailDisplay.textContent = user.email;
    loadMyMessages();
  } else {
    authLoggedOut.hidden = false;
    authLoggedIn.hidden = true;
    myMessagesList.innerHTML = "";
  }
}

async function loadMyMessages() {
  if (!currentUser) return;

  const { data, error } = await supabaseClient
    .from("contact_messages")
    .select("message, created_at")
    .eq("user_id", currentUser.id)
    .order("created_at", { ascending: false });

  if (error || !data || data.length === 0) {
    myMessagesList.innerHTML = '<li class="my-message__empty">아직 보낸 메시지가 없습니다.</li>';
    return;
  }

  myMessagesList.innerHTML = data
    .map((row) => {
      const date = new Date(row.created_at).toLocaleString("ko-KR");
      const message = row.message.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
      return `<li><div class="my-message__meta">${date}</div>${message}</li>`;
    })
    .join("");
}

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
});

signupBtn.addEventListener("click", async () => {
  authStatus.textContent = "";
  authStatus.className = "form-status";

  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;

  if (!email || password.length < 6) {
    authStatus.textContent = "이메일과 6자 이상의 비밀번호를 입력해 주세요.";
    authStatus.classList.add("form-status--error");
    return;
  }

  const { error } = await supabaseClient.auth.signUp({ email, password });

  if (error) {
    authStatus.textContent = "회원가입에 실패했습니다: " + error.message;
    authStatus.classList.add("form-status--error");
    return;
  }

  authStatus.textContent = "가입 확인 이메일을 보냈습니다. 메일함을 확인해 주세요.";
  authStatus.classList.add("form-status--success");
  authForm.reset();
});

logoutBtn.addEventListener("click", async () => {
  await supabaseClient.auth.signOut();
});

supabaseClient.auth.onAuthStateChange((_event, session) => {
  updateAuthUI(session ? session.user : null);
});

supabaseClient.auth.getSession().then(({ data }) => {
  updateAuthUI(data.session ? data.session.user : null);
});
