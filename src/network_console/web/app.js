// app.js —— 前端入口：i18n 渲染 + 后端健康指示灯
const CSRF_TOKEN = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = I18N.t(el.getAttribute("data-i18n"));
  });
  document.title = I18N.t("app.title");
  const btn = document.getElementById("lang-btn");
  if (btn) btn.textContent = I18N.lang === "zh" ? "EN" : "中";
}

async function checkHealth() {
  const dot = document.getElementById("backend-status");
  const text = document.getElementById("backend-status-text");
  try {
    const resp = await fetch("/api/health");
    const ok = resp.status === 200;
    dot.className = "status-dot " + (ok ? "ok" : "bad");
    text.textContent = I18N.t(ok ? "status.connected" : "status.disconnected");
  } catch (e) {
    dot.className = "status-dot bad";
    text.textContent = I18N.t("status.disconnected");
  }
}

document.getElementById("lang-btn").addEventListener("click", () => {
  I18N.setLang(I18N.lang === "zh" ? "en" : "zh");
});

applyI18n();
checkHealth();
