// modal.js —— 确认类弹窗（焦点陷阱）
//
// 不用 ES modules：本项目无构建步骤、<script> 标签顺序加载，全局命名空间最简。
//
// 用法：
//   UI.modal.confirm({
//     title: "确认删除？",
//     body: "此操作不可恢复。",        // 纯文本；或 bodyNode 传 DOM（二者选一，同传抛错）
//     okText: "确认", cancelText: "取消",  // 只接受字符串，i18n 由调用方处理
//     closeOnOverlay: true,
//     onOk: () => {}, onCancel: () => {}
//   });

(function () {
  "use strict";

  // 可聚焦选择器：未来弹窗里加输入框（如 DNS 切换输目标服务器）会自动进焦点循环
  const FOCUSABLE_SELECTOR =
    "button, input, select, textarea, [tabindex]:not([tabindex='-1'])";

  function confirm(opts) {
    const o = opts || {};

    // body 与 bodyNode 二选一：同传抛错，不静默
    if (o.body != null && o.bodyNode != null) {
      throw new Error("modal.confirm: body 与 bodyNode 不能同时传入");
    }

    const title = o.title != null ? String(o.title) : "";
    const okText = o.okText != null ? String(o.okText) : "确认";
    const cancelText = o.cancelText != null ? String(o.cancelText) : "取消";
    const closeOnOverlay = o.closeOnOverlay !== false; // 默认 true

    // 保存触发元素，关闭时焦点返回（不可用则回浏览器默认位置）
    const prevFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");

    const dialog = document.createElement("div");
    dialog.className = "modal";

    const titleId = "modal-title-" + Math.random().toString(36).slice(2, 8);
    const titleEl = document.createElement("div");
    titleEl.className = "modal-title";
    titleEl.id = titleId;
    titleEl.textContent = title;
    overlay.setAttribute("aria-labelledby", titleId);
    dialog.appendChild(titleEl);

    const bodyEl = document.createElement("div");
    bodyEl.className = "modal-body";
    if (o.bodyNode != null) {
      bodyEl.appendChild(o.bodyNode);
    } else {
      bodyEl.textContent = o.body != null ? String(o.body) : "";
    }
    dialog.appendChild(bodyEl);

    const actions = document.createElement("div");
    actions.className = "modal-actions";

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn-ghost";
    cancelBtn.textContent = cancelText;

    const okBtn = document.createElement("button");
    okBtn.className = "modal-btn-primary";
    okBtn.textContent = okText;

    actions.appendChild(cancelBtn);
    actions.appendChild(okBtn);
    dialog.appendChild(actions);

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    let closed = false;

    function getFocusables() {
      return Array.prototype.slice.call(overlay.querySelectorAll(FOCUSABLE_SELECTOR))
        .filter((el) => !el.disabled && el.offsetParent !== null);
    }

    function close(reason) {
      // reason: "cancel" → onCancel；"ok" → onOk；"" → 不触发任何回调
      if (closed) return; // 防双触发
      closed = true;

      document.removeEventListener("keydown", onKeydown);
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);

      // 焦点返回触发元素；不可用则回到浏览器默认位置
      if (prevFocus && document.contains(prevFocus)) prevFocus.focus();

      // 先清理再回调，回调抛异常也不会卡住弹窗
      if (reason === "ok" && typeof o.onOk === "function") o.onOk();
      else if (reason === "cancel" && typeof o.onCancel === "function") o.onCancel();
    }

    function onKeydown(e) {
      if (e.key === "Escape") {
        e.preventDefault();
        close("cancel");
      } else if (e.key === "Tab") {
        const focusables = getFocusables();
        if (!focusables.length) {
          e.preventDefault();
          return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        // 兜底：当前焦点不在弹窗内，强制拉回 first
        if (!focusables.includes(document.activeElement)) {
          e.preventDefault();
          first.focus();
          return;
        }
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    okBtn.addEventListener("click", () => close("ok"));
    cancelBtn.addEventListener("click", () => close("cancel"));
    overlay.addEventListener("mousedown", (e) => {
      if (e.target === overlay && closeOnOverlay) close("cancel");
    });
    document.addEventListener("keydown", onKeydown);

    // 打开时焦点落 OK 按钮
    requestAnimationFrame(() => okBtn.focus());

    return { el: overlay, close };
  }

  window.UI = window.UI || {};
  window.UI.modal = { confirm };
})();
