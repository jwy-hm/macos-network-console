// app.js —— 前端入口：i18n 渲染 + 状态总览 + 接口总览 + 健康指示灯
const CSRF_TOKEN = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";

const STATUS_CHECKS = [
  { id: "proxy", key: "status.proxy" },
  { id: "mesh", key: "status.mesh" },
  { id: "external", key: "status.external" },
  { id: "route_conflict", key: "status.route_conflict" },
  { id: "dns", key: "status.dns" },
  { id: "internal", key: "status.internal" },
  { id: "proxy_port", key: "status.proxy_port" },
  { id: "default_route", key: "status.default_route" },
];

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = I18N.t(el.getAttribute("data-i18n"));
  });
  document.title = I18N.t("app.title");
  const btn = document.getElementById("lang-btn");
  if (btn) btn.textContent = I18N.lang === "zh" ? "EN" : "中";
  // 重新渲染当前页（状态卡标签等）
  const active = document.querySelector(".nav-item.active");
  if (active) renderPage(active.dataset.page);
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

// ---- 状态总览 ----

function renderStatusSkeleton() {
  const grid = document.getElementById("status-grid");
  grid.innerHTML = "";
  STATUS_CHECKS.forEach((c) => {
    const card = document.createElement("div");
    card.className = "st";
    card.id = "st-" + c.id;
    card.innerHTML =
      '<div class="dot"></div><div class="txt"><div class="lbl">' +
      I18N.t(c.key) +
      '</div><div class="val">' +
      I18N.t("status.detecting") +
      "</div></div>";
    grid.appendChild(card);
  });
}

async function renderStatus() {
  renderStatusSkeleton();
  let data;
  try {
    data = await (await fetch("/api/status")).json();
  } catch (e) {
    return;
  }
  const byId = {};
  (data.checks || []).forEach((c) => (byId[c.id] = c));
  STATUS_CHECKS.forEach((sc) => {
    const c = byId[sc.id];
    const card = document.getElementById("st-" + sc.id);
    if (!c || !card) return;
    card.className = "st " + (c.ok ? "ok" : "bad");
    card.querySelector(".val").textContent = c.value;
    if (!c.ok && c.hint) {
      const hint = document.createElement("div");
      hint.className = "hint";
      hint.textContent = c.hint;
      card.querySelector(".txt").appendChild(hint);
    }
  });
}

// ---- 接口总览 ----

function humanBytes(n) {
  if (n == null) return "—";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  if (n < 1024 * 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + " MB";
  return (n / 1024 / 1024 / 1024).toFixed(2) + " GB";
}

function trafficSvg(ibytes, obytes, maxBytes) {
  const down = ((ibytes || 0) / maxBytes) * 100;
  const up = ((obytes || 0) / maxBytes) * 100;
  return (
    '<svg width="100%" height="10" viewBox="0 0 100 10" preserveAspectRatio="none" role="img">' +
    '<rect x="0" y="0" width="' + down + '" height="4" fill="#10b981"></rect>' +
    '<rect x="0" y="5.5" width="' + up + '" height="4" fill="#60a5fa"></rect>' +
    "</svg>"
  );
}

function interfaceCard(item, maxBytes) {
  const div = document.createElement("div");
  div.className = "iface " + (item.up ? "up" : "down");
  const addr = item.inet || item.inet6 || "—";
  div.innerHTML =
    '<div class="row1"><div class="dot"></div><span class="iname">' +
    item.name +
    '</span><span class="istate">' +
    I18N.t(item.up ? "interface.up" : "interface.down") +
    '</span></div>' +
    '<div class="row2"><span>' + addr + "</span>" +
    (item.mac ? '<span class="imac">' + item.mac + "</span>" : "") +
    '<span class="imtu">MTU ' + (item.mtu || "—") + "</span></div>" +
    '<div class="row3">' +
    '<span class="traffic">↓ ' + humanBytes(item.ibytes) + " / ↑ " + humanBytes(item.obytes) + "</span>" +
    "</div>" +
    trafficSvg(item.ibytes, item.obytes, maxBytes);
  return div;
}

async function renderInterfaces() {
  const list = document.getElementById("interface-list");
  list.innerHTML = '<div class="muted">' + I18N.t("status.detecting") + "</div>";
  let data;
  try {
    data = await (await fetch("/api/interface")).json();
  } catch (e) {
    list.innerHTML = '<div class="muted">加载失败</div>';
    return;
  }
  const ifs = data.interfaces || [];
  const maxBytes = Math.max(1, ...ifs.map((i) => (i.ibytes || 0) + (i.obytes || 0)));
  const dr = data.default_route || {};
  list.innerHTML = "";
  if (dr.interface || dr.gateway) {
    const g = document.createElement("div");
    g.className = "muted gateway";
    g.textContent = I18N.t("interface.gateway") + ": " + (dr.interface || "-") + " / " + (dr.gateway || "-");
    list.appendChild(g);
  }
  ifs.forEach((i) => list.appendChild(interfaceCard(i, maxBytes)));
}

// ---- 页面切换 ----

function renderPage(page) {
  if (page === "interface") renderInterfaces();
  else renderStatus();
}

function showPage(page) {
  document.querySelectorAll(".nav-item").forEach((n) => {
    n.classList.toggle("active", n.dataset.page === page);
  });
  document.getElementById("page-status").style.display = page === "status" ? "" : "none";
  document.getElementById("page-interface").style.display = page === "interface" ? "" : "none";
  renderPage(page);
}

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => showPage(item.dataset.page));
});

document.getElementById("lang-btn").addEventListener("click", () => {
  I18N.setLang(I18N.lang === "zh" ? "en" : "zh");
});

document.getElementById("btn-check").addEventListener("click", () => renderStatus());

applyI18n();
checkHealth();
renderStatus();
