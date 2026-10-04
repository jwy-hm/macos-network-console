// toast.js —— 轻量提示气泡（堆叠模式）
//
// 不用 ES modules：本项目无构建步骤、<script> 标签顺序加载，全局命名空间最简。
// 挂载到全局 UI 命名空间，与其他组件（modal/table）一致。
//
// 用法：
//   UI.toast("已复制", { type: "success" });
//   const t = UI.toast("加载中…", { type: "info", duration: 0 }); // 0 = 永久，手动关
//   t.dismiss();

(function () {
  "use strict";

  const MAX_STACK = 5; // 容器最多堆叠数，超出删最早

  function ensureContainer() {
    let c = document.getElementById("toast-container");
    if (!c) {
      c = document.createElement("div");
      c.id = "toast-container";
      document.body.appendChild(c);
    }
    return c;
  }

  function toast(message, opts) {
    const o = opts || {};
    const type = ["info", "success", "warn", "error"].indexOf(o.type) >= 0 ? o.type : "info";
    const duration = typeof o.duration === "number" ? o.duration : 3000;
    const showIcon = o.icon !== false; // 默认 true

    const container = ensureContainer();

    // 超出上限：删最早那个（用 firstElementChild，避免文本节点）
    // TODO(P2): 直接 removeChild 会让退场动画缺失，后续做堆叠滑出动画再优化
    while (container.children.length >= MAX_STACK) {
      const first = container.firstElementChild;
      if (first) container.removeChild(first);
    }

    const el = document.createElement("div");
    el.className = "toast toast-" + type;
    el.setAttribute("role", "status");

    if (showIcon) {
      const icon = document.createElement("span");
      icon.className = "toast-icon";
      icon.textContent = { info: "ℹ", success: "✓", warn: "⚠", error: "✕" }[type];
      el.appendChild(icon);
    }

    const text = document.createElement("span");
    text.className = "toast-text";
    text.textContent = String(message); // 纯文本，杜绝 XSS
    el.appendChild(text);

    container.appendChild(el);

    // 入场动画：下一帧加 show class
    requestAnimationFrame(() => el.classList.add("show"));

    let timer = null;
    let dismissed = false;
    function dismiss() {
      if (dismissed) return; // 幂等保护：防双触发
      if (!el.parentNode) return; // 已从 DOM 移除
      dismissed = true;
      if (timer) clearTimeout(timer);
      el.classList.remove("show");
      // 等退场动画结束后移除
      el.addEventListener("transitionend", () => {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, { once: true });
      // 兜底：无 transition 或事件未触发时强制移除
      setTimeout(() => {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 400);
    }

    if (duration > 0) {
      timer = setTimeout(dismiss, duration);
    }

    return { el, dismiss };
  }

  window.UI = window.UI || {};
  window.UI.toast = toast;
})();
