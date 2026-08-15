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
