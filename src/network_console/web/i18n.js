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
      "nav.interfaces": "网络接口",
      "status.title": "系统状态",
      "status.connected": "后端已连接",
      "status.disconnected": "后端未连接",
      "status.detecting": "检测中…",
      "status.proxy": "代理客户端",
      "status.mesh": "内网互联",
      "status.external": "外网连通性",
      "status.route_conflict": "路由冲突",
      "status.dns": "DNS 解析",
      "status.internal": "内网设备",
      "status.proxy_port": "代理监听端口",
      "status.default_route": "默认路由",
      "common.refresh": "重新检测",
      "interface.title": "网络接口",
      "interface.gateway": "默认网关",
      "interface.up": "已启用",
      "interface.down": "已停用",
      "interface.download": "下行",
      "interface.upload": "上行",
    },
    en: {
      "app.title": "Network Console",
      "app.subtitle": "Local network management",
      "nav.overview": "Overview",
      "nav.interfaces": "Interfaces",
      "status.title": "System Status",
      "status.connected": "Backend connected",
      "status.disconnected": "Backend disconnected",
      "status.detecting": "Detecting…",
      "status.proxy": "Proxy client",
      "status.mesh": "Mesh / VPN",
      "status.external": "External connectivity",
      "status.route_conflict": "Route conflict",
      "status.dns": "DNS",
      "status.internal": "Internal peers",
      "status.proxy_port": "Proxy port",
      "status.default_route": "Default route",
      "common.refresh": "Refresh",
      "interface.title": "Interfaces",
      "interface.gateway": "Default gateway",
      "interface.up": "Up",
      "interface.down": "Down",
      "interface.download": "Download",
      "interface.upload": "Upload",
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
