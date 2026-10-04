// table.js —— 通用表格
//
// 不用 ES modules：本项目无构建步骤、<script> 标签顺序加载，全局命名空间最简。
//
// 用法：
//   UI.table.render(container, {
//     columns: [
//       { key: "rank", label: "#" },
//       { key: "domain", label: "域名", sortable: true },
//       { key: "ms", label: "延迟", sortable: true,
//         sortValue: (r) => r.ms ?? Infinity,      // 排序用（数字/字符串）
//         format: (v, r) => v == null ? "—" : v + " ms" }  // 展示用
//     ],
//     rows: [...],
//     sortable: true,        // 总开关：点击表头排序
//     stickyHeader: true,    // 表头 position: sticky; top: 0
//     emptyText: "无数据",
//     onRowClick: (row, index) => {}   // index = 当前显示顺序的索引（排序后）
//   });
//
// render(container, opts) 语义：替换 container 全部内容，幂等（重复调用覆盖旧表）。
// 返回值 { el, render }：render(rows, {preserveSort}) 更新数据；默认保留上次排序。

(function () {
  "use strict";

  function cellValue(col, row) {
    if (typeof col.sortValue === "function") return col.sortValue(row);
    return row[col.key];
  }

  function cellText(col, row) {
    const raw = row[col.key];
    if (typeof col.format === "function") return col.format(raw, row);
    return raw == null ? "" : String(raw);
  }

  function render(container, opts) {
    const o = opts || {};
    const columns = o.columns || [];
    const sortable = o.sortable !== false; // 默认 true
    const stickyHeader = o.stickyHeader !== false; // 默认 true
    const emptyText = o.emptyText != null ? o.emptyText : "无数据";

    let rows = (o.rows || []).slice();
    let sortCol = null; // 当前排序列 key
    let sortDir = 1;    // 1 升序，-1 降序

    // 幂等：清空容器
    container.textContent = "";

    const table = document.createElement("table");
    table.className = "ui-table";
    if (stickyHeader) table.classList.add("sticky");

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    columns.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col.label != null ? String(col.label) : col.key;
      if (col.width != null) th.style.width = col.width;
      if (col.sortable && sortable) {
        th.className = "sortable";
        th.setAttribute("data-key", col.key);
        th.addEventListener("click", () => {
          if (sortCol === col.key) {
            sortDir = -sortDir;
          } else {
            sortCol = col.key;
            sortDir = 1;
          }
          reSort();
          updateHeaderClasses();
        });
      }
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    table.appendChild(tbody);

    container.appendChild(table);

    function updateHeaderClasses() {
      headRow.querySelectorAll("th").forEach((th) => {
        th.classList.remove("sorted-asc", "sorted-desc");
        if (th.getAttribute("data-key") === sortCol) {
          th.classList.add(sortDir === 1 ? "sorted-asc" : "sorted-desc");
        }
      });
    }

    // 排序比较：非有限数（null/undefined/NaN）排最后；数字数值比较，其余字符串比较
    function compare(col, a, b) {
      const va = cellValue(col, a);
      const vb = cellValue(col, b);
      const na = typeof va === "number" && isFinite(va);
      const nb = typeof vb === "number" && isFinite(vb);
      if (na && nb) return (va - vb) * sortDir;
      if (na && !nb) return -1; // 无值总排最后，与 sortDir 无关
      if (!na && nb) return 1;  // 无值总排最后，与 sortDir 无关
      return String(va).localeCompare(String(vb)) * sortDir;
    }

    function reSort() {
      if (!sortCol) return;
      const col = columns.find((c) => c.key === sortCol);
      if (!col) return;
      rows.sort((a, b) => compare(col, a, b));
      fillBody();
    }

    function fillBody() {
      tbody.textContent = "";
      if (!rows.length) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = columns.length || 1;
        td.className = "ui-table-empty";
        td.textContent = emptyText;
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
      }
      rows.forEach((row, index) => {
        const tr = document.createElement("tr");
        columns.forEach((col) => {
          const td = document.createElement("td");
          td.textContent = cellText(col, row); // 纯文本，杜绝 XSS
          tr.appendChild(td);
        });
        if (typeof o.onRowClick === "function") {
          tr.className = "clickable";
          // index = 当前显示顺序的索引（排序后的位置，非原始数据下标）
          tr.addEventListener("click", () => o.onRowClick(row, index));
        }
        tbody.appendChild(tr);
      });
    }

    fillBody();

    return {
      el: table,
      render(newRows, renderOpts) {
        const ro = renderOpts || {};
        const preserveSort = ro.preserveSort !== false; // 默认保留上次排序
        rows = (newRows || []).slice();
        if (!preserveSort) {
          sortCol = null;
          sortDir = 1;
          updateHeaderClasses();
        }
        if (sortCol) {
          reSort();
        } else {
          fillBody();
        }
      },
    };
  }

  window.UI = window.UI || {};
  window.UI.table = { render };
})();
