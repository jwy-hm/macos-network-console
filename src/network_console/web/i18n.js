// i18n.js —— 文案集中管理，切换语言触发全页重渲染
const I18N = {
  lang: (function () {
    const saved = localStorage.getItem("mnc.lang");
    if (saved === "zh" || saved === "en") return saved;
    return (navigator.language || "en").toLowerCase().startsWith("zh") ? "zh" : "en";
  })(),
  dict: {
    zh: {
      "app.title": "网络控制台",
      "app.subtitle": "本机网络管理",
      "nav.overview": "总览",
      "nav.interfaces": "网络接口（即将上线）",
      "nav.diagnostics": "诊断（即将上线）",
      "status.title": "系统状态",
      "status.connected": "后端已连接",
      "status.disconnected": "后端未连接",
      "status.placeholder": "状态总览将在下一批实现。",
      "common.refresh": "重新检测",
    },
    en: {
      "app.title": "Network Console",
      "app.subtitle": "Local network management",
      "nav.overview": "Overview",
      "nav.interfaces": "Interfaces (coming soon)",
      "nav.diagnostics": "Diagnostics (coming soon)",
      "status.title": "System Status",
      "status.connected": "Backend connected",
      "status.disconnected": "Backend disconnected",
      "status.placeholder": "Status overview will be implemented in the next batch.",
      "common.refresh": "Refresh",
    },
  },
  t(key) {
    return (this.dict[this.lang] && this.dict[this.lang][key]) || key;
  },
  setLang(lang) {
    this.lang = lang === "zh" ? "zh" : "en";
    localStorage.setItem("mnc.lang", this.lang);
    applyI18n();
  },
};
