// app.js — frontend entry: i18n, status overview, interfaces, connections, diagnostics, settings
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

// ---- theme (follow / light / dark) ----

const THEME_KEY = "mnc.theme";
const PRIVACY_KEY = "mnc.privacy";

function getTheme() {
  const t = localStorage.getItem(THEME_KEY);
  return t === "light" || t === "dark" || t === "follow" ? t : "follow";
}

function applyTheme() {
  const mode = getTheme();
  let eff = mode;
  if (mode === "follow") {
    eff = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  document.documentElement.setAttribute("data-theme", eff);
}

function setTheme(mode) {
  localStorage.setItem(THEME_KEY, mode);
  applyTheme();
  showSaved();
}

function initTheme() {
  applyTheme();
  // follow mode: react to system theme changes immediately
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (getTheme() === "follow") applyTheme();
  });
}

// ---- privacy mode ----
//
// Masking contract (Option A): every sensitive value funnels through maskMac /
// maskFakeIp below. Any future copy / export feature MUST route values through
// these same helpers, so masked display is never bypassed — raw values live in
// memory only and must not be written to clipboard or exported files verbatim.

function privacyOn() {
  return localStorage.getItem(PRIVACY_KEY) === "1";
}

function maskMac(mac) {
  if (!mac) return mac;
  return mac.replace(/[0-9a-f]{2}/gi, "\u2022\u2022");
}

function maskFakeIp(text) {
  if (!text) return text;
  let out = String(text);
  out = out.replace(/\b198\.18\.\d{1,3}\.\d{1,3}\b/g, "\u2022\u2022\u2022");
  out = out.replace(/\b240\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, "\u2022\u2022\u2022");
  return out;
}

function maskSsid(ssid) {
  if (!ssid) return ssid;
  return ssid.replace(/./g, "\u2022");
}

function maskBssid(bssid) {
  if (!bssid) return bssid;
  return "\u2022\u2022:\u2022\u2022:\u2022\u2022:\u2022\u2022:\u2022\u2022:\u2022\u2022";
}

// ---- i18n ----

let currentPage = "status";

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = I18N.t(el.getAttribute("data-i18n"));
  });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
    el.placeholder = I18N.t(el.getAttribute("data-i18n-ph"));
  });
  document.title = I18N.t("app.title");
  const btn = document.getElementById("lang-btn");
  if (btn) btn.textContent = I18N.t("lang.toggle");
  // re-render current page (status labels, etc.)
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

// ---- status overview ----

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

// ---- interfaces overview ----

function humanBytes(n) {
  if (n == null) return "\u2014";
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
  const addr = item.inet || item.inet6 || "\u2014";
  const mac = privacyOn() ? maskMac(item.mac) : item.mac;
  div.innerHTML =
    '<div class="row1"><div class="dot"></div><span class="iname">' +
    item.name +
    '</span><span class="istate">' +
    I18N.t(item.up ? "interface.up" : "interface.down") +
    '</span></div>' +
    '<div class="row2"><span>' + addr + "</span>" +
    (mac ? '<span class="imac">' + mac + "</span>" : "") +
    '<span class="imtu">MTU ' + (item.mtu || "\u2014") + "</span></div>" +
    '<div class="row3">' +
    '<span class="traffic">\u2193 ' + humanBytes(item.ibytes) + " / \u2191 " + humanBytes(item.obytes) + "</span>" +
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
    list.innerHTML = '<div class="muted">' + I18N.t("common.loadFailed") + "</div>";
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

// ---- connections ----

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
  const remote = c.remote ? " \u2192 " + c.remote : "";
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
    " \u00b7 " +
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
      list.innerHTML = '<div class="muted">' + I18N.t("common.loadFailed") + "</div>";
      return;
    }
  }
  renderConnList();
}

// ---- diagnostics toolbox ----

const DIAG_TOOLS = [
  { id: "ping", target: "8.8.8.8", cap: "ping" },
  { id: "traceroute", target: "8.8.8.8", cap: "traceroute" },
  { id: "http", target: "https://example.com", cap: "curl" },
  { id: "dns", target: "example.com", cap: "dig" },
];

let diagMeta = null; // { tools: {...}, timeouts: {...} }
let diagHistory = [];

function toolAvailable(tool) {
  if (!diagMeta) return false;
  const tools = diagMeta.tools || {};
  if (tool.id === "dns") return !!(tools.dig || tools.nslookup);
  return !!tools[tool.cap];
}

function toolTimeout(toolId) {
  if (diagMeta && diagMeta.timeouts && diagMeta.timeouts[toolId]) return diagMeta.timeouts[toolId];
  return 15;
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
      "DNS " + (t.namelookup || "-") + "s \u00b7 connect " + (t.connect || "-") +
      "s \u00b7 TLS " + (t.appconnect || "-") + "s \u00b7 TTFB " + (t.starttransfer || "-") + "s";
  }
  const summary = privacyOn() ? maskFakeIp(r.summary) : r.summary;
  let warning = "";
  if (r.warning) {
    warning = '<div class="diag-warning">' + I18N.t("diag.warning." + r.warning) + "</div>";
  }
  div.innerHTML =
    '<div class="diag-result-head">' +
    '<span class="diag-result-tool">' + escapeHtml(r.tool) + "</span>" +
    '<span class="diag-result-target">' + escapeHtml(r.target) + "</span>" +
    '<span class="diag-result-summary">' + escapeHtml(summary) + "</span>" +
    "</div>" +
    (detail ? '<div class="diag-result-detail">' + escapeHtml(detail) + "</div>" : "") +
    warning +
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
  if (!diagMeta) {
    try {
      diagMeta = await (await fetch("/api/diagnostics/tools")).json();
    } catch (e) {
      diagMeta = { tools: {}, timeouts: {} };
    }
  }
  renderDiagToolCards();
  renderDiagResults();
}

async function runDiag(toolId) {
  const input = document.getElementById("diag-target-" + toolId);
  const target = input.value.trim();
  if (!target) return;
  const timeout = toolTimeout(toolId);
  const statusEl = document.getElementById("diag-status-" + toolId);
  statusEl.textContent = I18N.t("diag.running").replace("{t}", timeout);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout * 1000);
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
    result = { ok: false, tool: toolId, target: target, summary: I18N.t("diag.timeout").replace("{t}", timeout), detail: {}, raw: "" };
  } finally {
    clearTimeout(timer);
    statusEl.textContent = "";
  }
  diagHistory.push(result);
  renderDiagResults();
}

// ---- wifi ----

let wifiData = null;
let ssidRevealed = false;
let preferredData = null;

function signalBars(grade) {
  const levels = { excellent: 4, good: 3, fair: 2, poor: 1, unknown: 0 };
  const n = levels[grade] || 0;
  let rects = "";
  for (let i = 0; i < 4; i++) {
    const on = i < n;
    const h = (i + 1) * 3;
    rects += '<rect x="' + (i * 7) + '" y="' + (12 - h) + '" width="5" height="' + h + '" rx="0.5" fill="' + (on ? "var(--accent)" : "var(--line)") + '"></rect>';
  }
  return '<svg class="wifi-bars" width="28" height="12" viewBox="0 0 28 12" role="img">' + rects + "</svg>";
}

function wifiSecurityLabel(key) {
  if (!key) return "\u2014";
  return I18N.t("wifi.security." + key) || key;
}

function wifiGradeLabel(grade) {
  return I18N.t("wifi.grade." + grade) || grade;
}

function wifiField(labelKey, value) {
  return '<div class="wifi-field"><span class="wifi-label">' + I18N.t(labelKey) +
    '</span><span class="wifi-value">' + escapeHtml(String(value)) + "</span></div>";
}

function renderWifiContent() {
  const content = document.getElementById("wifi-content");
  if (!wifiData || !wifiData.connected) {
    content.innerHTML = '<div class="muted">' + I18N.t("wifi.not_connected") +
      (wifiData && wifiData.device ? " (" + escapeHtml(wifiData.device) + ")" : "") + "</div>";
    return;
  }
  const d = wifiData;
  const sig = d.signal || {};
  const showSsid = ssidRevealed && !privacyOn();
  const ssidText = showSsid ? d.ssid : maskSsid(d.ssid);
  const bssid = d.bssid ? maskBssid(d.bssid) : I18N.t("wifi.bssid.unavailable");
  const rate = d.rate_mbps != null ? d.rate_mbps + " Mbps" : "\u2014";
  const eyeBtn = privacyOn()
    ? ""
    : '<button id="wifi-reveal" class="btn-ghost btn-mini" title="' + I18N.t("wifi.reveal") + '">\uD83D\uDC41</button>';
  let note = "";
  if (sig.note === "low_snr") {
    note = '<div class="diag-warning">' + I18N.t("wifi.note.low_snr") + "</div>";
  }
  content.innerHTML =
    '<div class="wifi-head">' +
    '<span class="wifi-ssid" id="wifi-ssid-text">' + escapeHtml(ssidText) + "</span>" +
    eyeBtn +
    signalBars(sig.grade) +
    '<span class="wifi-grade grade-' + escapeHtml(sig.grade) + '">' + wifiGradeLabel(sig.grade) + "</span>" +
    "</div>" +
    '<div class="wifi-grid">' +
    wifiField("wifi.device", d.device) +
    wifiField("wifi.security", wifiSecurityLabel(d.security)) +
    wifiField("wifi.channel", d.channel || "\u2014") +
    wifiField("wifi.phymode", d.phymode || "\u2014") +
    wifiField("wifi.rate", rate) +
    wifiField("wifi.bssid", bssid) +
    wifiField("wifi.rssi", sig.rssi != null ? sig.rssi + " dBm" : "\u2014") +
    wifiField("wifi.noise", sig.noise != null ? sig.noise + " dBm" : "\u2014") +
    wifiField("wifi.snr", sig.snr != null ? sig.snr + " dB" : "\u2014") +
    "</div>" +
    note +
    '<div id="wifi-preferred"></div>';
  const revealBtn = document.getElementById("wifi-reveal");
  if (revealBtn) {
    revealBtn.addEventListener("click", () => {
      ssidRevealed = !ssidRevealed;
      document.getElementById("wifi-ssid-text").textContent =
        (ssidRevealed && !privacyOn()) ? wifiData.ssid : maskSsid(wifiData.ssid);
    });
  }
  renderPreferredSection();
}

function renderPreferredSection() {
  const wrap = document.getElementById("wifi-preferred");
  if (!wrap) return;
  wrap.innerHTML = '<button id="wifi-preferred-btn" class="btn-ghost">' + I18N.t("wifi.preferred.show") + "</button>";
  document.getElementById("wifi-preferred-btn").addEventListener("click", () => loadPreferred());
}

async function loadPreferred() {
  const wrap = document.getElementById("wifi-preferred");
  if (preferredData) {
    renderPreferredList(wrap);
    return;
  }
  const privacy = privacyOn() ? "1" : "0";
  try {
    preferredData = await (await fetch("/api/wifi/preferred?privacy=" + privacy)).json();
  } catch (e) {
    preferredData = null;
  }
  renderPreferredList(wrap);
}

function renderPreferredList(wrap) {
  if (!preferredData) {
    wrap.innerHTML = '<div class="muted">' + I18N.t("common.loadFailed") + "</div>";
    return;
  }
  if (preferredData.masked) {
    wrap.innerHTML = '<div class="muted">' + I18N.t("wifi.preferred.masked") + "</div>";
    return;
  }
  const nets = preferredData.networks || [];
  let html = '<div class="wifi-preferred-title">' + I18N.t("wifi.preferred.title") + " (" + nets.length + ")</div>";
  if (!nets.length) {
    html += '<div class="muted">' + I18N.t("wifi.preferred.empty") + "</div>";
  } else {
    html += '<div class="wifi-preferred-list">';
    nets.forEach((n) => { html += '<span class="wifi-chip">' + escapeHtml(n) + "</span>"; });
    html += "</div>";
  }
  wrap.innerHTML = html;
}

async function renderWifi() {
  const content = document.getElementById("wifi-content");
  if (!wifiData) {
    content.innerHTML = '<div class="muted">' + I18N.t("status.detecting") + "</div>";
    try {
      wifiData = await (await fetch("/api/wifi")).json();
    } catch (e) {
      wifiData = null;
      content.innerHTML = '<div class="muted">' + I18N.t("common.loadFailed") + "</div>";
      return;
    }
  }
  renderWifiContent();
}

// ---- settings ----

function showSaved() {
  const el = document.getElementById("settings-saved");
  if (!el) return;
  el.style.display = "";
  clearTimeout(showSaved._t);
  showSaved._t = setTimeout(() => { el.style.display = "none"; }, 1500);
}

function renderSettings() {
  const mode = getTheme();
  document.querySelectorAll('input[name="theme"]').forEach((r) => { r.checked = r.value === mode; });
  const pt = document.getElementById("privacy-toggle");
  if (pt) pt.checked = privacyOn();
}

// ---- page switching ----

function renderPage(page) {
  if (page === "interface") renderInterfaces();
  else if (page === "wifi") renderWifi();
  else if (page === "connection") renderConnections();
  else if (page === "diagnostics") renderDiagnostics();
  else if (page === "settings") renderSettings();
  else renderStatus();
}

function showPage(page) {
  currentPage = page;
  document.querySelectorAll(".nav-item").forEach((n) => {
    n.classList.toggle("active", n.dataset.page === page);
  });
  ["status", "interface", "wifi", "connection", "diagnostics", "settings"].forEach((p) => {
    document.getElementById("page-" + p).style.display = p === page ? "" : "none";
  });
  renderPage(page);
}

// ---- event listeners ----

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

document.querySelectorAll('input[name="theme"]').forEach((r) => {
  r.addEventListener("change", () => { if (r.checked) setTheme(r.value); });
});

document.getElementById("privacy-toggle").addEventListener("change", (e) => {
  localStorage.setItem(PRIVACY_KEY, e.target.checked ? "1" : "0");
  showSaved();
  renderPage(currentPage);
});

// ---- init ----

initTheme();
applyI18n();
checkHealth();
renderStatus();
