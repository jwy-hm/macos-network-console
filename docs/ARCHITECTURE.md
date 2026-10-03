# 架构说明

## 总体结构

- **后端**：Python 标准库 `http.server`（无 FastAPI/uvicorn），只监听 `127.0.0.1`。
- **前端**：单页 HTML + 原生 JS，无构建步骤、无 CDN，静态资源由 `server.py` 白名单路由。
- **平台层**：`core/platform_macos.py` 封装 macOS 命令，统一走 `core.shell.run`（白名单 + 超时）。
- **API 层**：`api/*.py` 解析平台层输出为结构化 JSON，路由集中在 `server.py`。

## 验证方法

分层验证，缺一不可：

- **API 层**：`curl` + pytest。pytest 含单元测试（mock `core.shell.run`）与
  起真实服务的 raw socket 对抗测试（`tests/test_security.py`）。
- **页面层**：必须用真浏览器或 headless 打开，确认 JS/CSS 实际加载、页面可交互。
  `curl` 只能拿到 HTML 源码，**看不到 JS 是否加载成功**。
  P0 阶段曾因此漏掉「静态资源未路由、前端白屏」的 bug（commit `b848ae9`），
  教训是：API 全绿 ≠ 页面可用。
- **冒烟**：`make smoke` 起服务后逐个检查首页 + 全部静态资源都返回 200。

## 每批交付前的五绿

```
make lint && make test && make smoke && make privacy-check && make i18n-check
```

五绿通过才算完成，才可开 PR。
