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

// --- View switching ---
// The header stays fixed; only the <main> content swaps between these views.

const views = {
  home: document.getElementById("viewHome"),
  auth: document.getElementById("viewAuth"),
  recovery: document.getElementById("viewRecovery"),
  recoveryComplete: document.getElementById("viewRecoveryComplete"),
  messages: document.getElementById("viewMessages"),
};

function showView(name) {
  Object.values(views).forEach((el) => {
    el.hidden = true;
  });
  views[name].hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll(".home-link").forEach((link) => {
  link.addEventListener("click", () => showView("home"));
});

// --- Contact form ---

const contactForm = document.getElementById("contactForm");
const formStatus = document.getElementById("formStatus");

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
});

// --- Nav auth controls ---

const navLoggedOut = document.getElementById("navLoggedOut");
const navLoggedIn = document.getElementById("navLoggedIn");
const messagesUserEmail = document.getElementById("messagesUserEmail");
const navLoginBtn = document.getElementById("navLoginBtn");
const navSignupBtn = document.getElementById("navSignupBtn");
const navMessagesBtn = document.getElementById("navMessagesBtn");
const navLogoutBtn = document.getElementById("navLogoutBtn");

navLoginBtn.addEventListener("click", () => showView("auth"));
navSignupBtn.addEventListener("click", () => showView("auth"));
navMessagesBtn.addEventListener("click", () => {
  showView("messages");
  loadMyMessages();
});

navLogoutBtn.addEventListener("click", async () => {
  await supabaseClient.auth.signOut();
  showView("home");
});

function updateAuthUI(user) {
  currentUser = user;

  if (user) {
    navLoggedOut.hidden = true;
    navLoggedIn.hidden = false;
    messagesUserEmail.textContent = user.email;
  } else {
    navLoggedOut.hidden = false;
    navLoggedIn.hidden = true;
  }
}

// --- Login / signup ---

const authForm = document.getElementById("authForm");
const authStatus = document.getElementById("authStatus");
const signupBtn = document.getElementById("signupBtn");
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

goToLoginBtn.addEventListener("click", () => {
  showView("auth");
});

// --- My messages ---

const myMessagesList = document.getElementById("myMessages");

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
