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
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
    el.placeholder = I18N.t(el.getAttribute("data-i18n-ph"));
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

// ---- 连接监控 ----

let connData = null;

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function connFilter() {
  if (!connData) return [];
  const proc = (document.getElementById("conn-filter-proc").value || "").toLowerCase();
  const port = (document.getElementById("conn-filter-port").value || "").trim();
  return connData.connections.filter((c) => {
    const okProc = !proc || (c.command || "").toLowerCase().indexOf(proc) >= 0;
    const okPort =
      !port ||
      (c.local && c.local.indexOf(":" + port) >= 0) ||
      (c.remote && c.remote.indexOf(":" + port) >= 0);
    return okProc && okPort;
  });
}

function connCard(c) {
  const div = document.createElement("div");
  div.className = "conn" + (c.state === "LISTEN" ? " listen" : "");
  const remote = c.remote ? " → " + c.remote : "";
  const state = c.state ? '<span class="conn-state">' + escapeHtml(c.state) + "</span>" : "";
  div.innerHTML =
    '<span class="conn-proc">' + escapeHtml(c.command) + "</span>" +
    '<span class="conn-pid">' + escapeHtml(c.pid) + "</span>" +
    '<span class="conn-proto">' + escapeHtml(c.proto) + "</span>" +
    '<span class="conn-addr">' + escapeHtml(c.local) + escapeHtml(remote) + "</span>" +
    state;
  return div;
}

function renderConnList() {
  const list = document.getElementById("conn-list");
  const meta = document.getElementById("conn-meta");
  if (!connData) return;
  const conns = connFilter();
  const shown = conns.length;
  const total = connData.total;
  meta.textContent =
    I18N.t("conn.scope") +
    " · " +
    (connData.truncated
      ? I18N.t("conn.truncated").replace("{shown}", shown).replace("{total}", total)
      : I18N.t("conn.count").replace("{shown}", shown).replace("{total}", total));
  list.innerHTML = "";
  if (!conns.length) {
    list.innerHTML = '<div class="muted">' + I18N.t("conn.empty") + "</div>";
    return;
  }
  conns.forEach((c) => list.appendChild(connCard(c)));
}

async function renderConnections() {
  const list = document.getElementById("conn-list");
  if (!connData) {
    list.innerHTML = '<div class="muted">' + I18N.t("status.detecting") + "</div>";
    try {
      connData = await (await fetch("/api/connection")).json();
    } catch (e) {
      connData = null;
      list.innerHTML = '<div class="muted">加载失败</div>';
      return;
    }
  }
  renderConnList();
}

// ---- 诊断工具箱 ----

const DIAG_TOOLS = [
  { id: "ping", target: "8.8.8.8", cap: "ping" },
  { id: "traceroute", target: "8.8.8.8", cap: "traceroute" },
  { id: "http", target: "https://example.com", cap: "curl" },
  { id: "dns", target: "example.com", cap: "dig" },
];

let diagTools = null;
let diagHistory = [];

function toolAvailable(tool) {
  if (!diagTools) return false;
  if (tool.id === "dns") return !!(diagTools.dig || diagTools.nslookup);
  return !!diagTools[tool.cap];
}

function renderDiagToolCards() {
  const wrap = document.getElementById("diag-tools");
  wrap.innerHTML = "";
  DIAG_TOOLS.forEach((tool) => {
    const avail = toolAvailable(tool);
    const card = document.createElement("div");
    card.className = "diag-tool";
    card.innerHTML =
      '<div class="diag-head"><span class="diag-name">' +
      I18N.t("diag." + tool.id + ".name") +
      "</span>" +
      (avail ? "" : '<span class="diag-unavail">' + I18N.t("diag.unavailable") + "</span>") +
      "</div>" +
      '<div class="diag-desc">' +
      I18N.t("diag." + tool.id + ".desc") +
      "</div>" +
      '<div class="diag-row">' +
      '<input id="diag-target-' + tool.id + '" class="input" value="' + escapeHtml(tool.target) + '" autocomplete="off">' +
      '<button id="diag-run-' + tool.id + '" class="btn-ghost"' + (avail ? "" : " disabled") + ">" +
      I18N.t("diag.run") +
      "</button>" +
      "</div>" +
      '<div id="diag-status-' + tool.id + '" class="diag-status"></div>';
    wrap.appendChild(card);
    if (avail) {
      document.getElementById("diag-run-" + tool.id).addEventListener("click", () => runDiag(tool.id));
    }
  });
}

function diagResultCard(r) {
  const div = document.createElement("div");
  div.className = "diag-result " + (r.ok ? "ok" : "bad");
  let detail = "";
  if (r.tool === "ping" && r.detail) {
    detail =
      "transmitted=" + r.detail.transmitted +
      " received=" + r.detail.received +
      " loss=" + r.detail.loss + "%";
    if (r.detail.rtt && r.detail.rtt.avg != null) detail += " avg=" + r.detail.rtt.avg + "ms";
  } else if (r.tool === "http" && r.detail && r.detail.timing) {
    const t = r.detail.timing;
    detail =
      "DNS " + (t.namelookup || "-") + "s · 连接 " + (t.connect || "-") +
      "s · TLS " + (t.appconnect || "-") + "s · 首字节 " + (t.starttransfer || "-") + "s";
  }
  div.innerHTML =
    '<div class="diag-result-head">' +
    '<span class="diag-result-tool">' + escapeHtml(r.tool) + "</span>" +
    '<span class="diag-result-target">' + escapeHtml(r.target) + "</span>" +
    '<span class="diag-result-summary">' + escapeHtml(r.summary) + "</span>" +
    "</div>" +
    (detail ? '<div class="diag-result-detail">' + escapeHtml(detail) + "</div>" : "") +
    (r.raw ? '<details class="diag-raw"><summary>' + I18N.t("diag.raw") + "</summary><pre>" + escapeHtml(r.raw) + "</pre></details>" : "");
  return div;
}

function renderDiagResults() {
  const wrap = document.getElementById("diag-results");
  wrap.innerHTML = "";
  if (!diagHistory.length) return;
  const title = document.createElement("div");
  title.className = "diag-results-title";
  title.textContent = I18N.t("diag.results");
  wrap.appendChild(title);
  diagHistory.forEach((r) => wrap.appendChild(diagResultCard(r)));
}

async function renderDiagnostics() {
  if (!diagTools) {
    try {
      const resp = await (await fetch("/api/diagnostics/tools")).json();
      diagTools = resp.tools || {};
    } catch (e) {
      diagTools = {};
    }
  }
  renderDiagToolCards();
  renderDiagResults();
}

async function runDiag(toolId) {
  const input = document.getElementById("diag-target-" + toolId);
  const target = input.value.trim();
  if (!target) return;
  const statusEl = document.getElementById("diag-status-" + toolId);
  statusEl.textContent = I18N.t("diag.running");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  let result;
  try {
    const resp = await fetch("/api/diagnostics/run", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify({ tool: toolId, target: target }),
      signal: controller.signal,
    });
    result = await resp.json();
  } catch (e) {
    result = { ok: false, tool: toolId, target: target, summary: I18N.t("diag.timeout"), detail: {}, raw: "" };
  } finally {
    clearTimeout(timer);
    statusEl.textContent = "";
  }
  diagHistory.push(result);
  renderDiagResults();
}

// ---- 页面切换 ----

function renderPage(page) {
  if (page === "interface") renderInterfaces();
  else if (page === "connection") renderConnections();
  else if (page === "diagnostics") renderDiagnostics();
  else renderStatus();
}

function showPage(page) {
  document.querySelectorAll(".nav-item").forEach((n) => {
    n.classList.toggle("active", n.dataset.page === page);
  });
  ["status", "interface", "connection", "diagnostics"].forEach((p) => {
    document.getElementById("page-" + p).style.display = p === page ? "" : "none";
  });
  renderPage(page);
}

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => showPage(item.dataset.page));
});

document.getElementById("lang-btn").addEventListener("click", () => {
  I18N.setLang(I18N.lang === "zh" ? "en" : "zh");
});

document.getElementById("btn-check").addEventListener("click", () => renderStatus());

document.getElementById("conn-filter-proc").addEventListener("input", renderConnList);
document.getElementById("conn-filter-port").addEventListener("input", renderConnList);
document.getElementById("diag-clear").addEventListener("click", () => {
  diagHistory = [];
  renderDiagResults();
});

applyI18n();
checkHealth();
renderStatus();
