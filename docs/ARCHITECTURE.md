[**简体中文**](ARCHITECTURE.md) | [English](ARCHITECTURE.en.md)

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

## Known Limitations

以下为已知局限，属于有意为之或待后续版本处理，非 bug：

- **`$USER` 裸词匹配的脆弱性**：`privacy_check.py` 的 `$USER` 动态黑名单用词边界匹配，
  会把代码里同名的通用标识符（如 CI 上的 `runner`、变量名）误报。当前靠 `_SKIP_USERS`
  跳过集缓解，但跳过集没有收敛终点（每遇一个新环境词就要加一条）。后续方向：改为
  「只在明确上下文匹配用户名」（如 `/Users/<name>/`、`<name>@host`），而非全文裸词扫。
- **TUN 代理下的诊断局限**：traceroute 全空跳、DNS 返回 fake-ip 是代理软件的正常行为，
  详见 README「环境提示」。
- **页面层渲染尚未接入自动化验证**：`make smoke` 只验证静态资源 200，不验证 JS 渲染
  和交互。计划引入 playwright 做 `make ui-smoke`，彻底堵住「渲染没验证」的盲区。
- **Wi-Fi 信道 / 速率字段未结构化**：`channel` 是拼好的显示串（`"36 (5GHz, 40MHz)"`），
  未拆成 `channel`/`band`/`width_mhz` 三个字段；`rate_mbps` 是 Tx 速率，未标注方向。
  留待 P2 做信道拥塞可视化时一并处理。
- **MAC / fake-ip 遮罩仍是前端行为**：隐私模式下 MAC 与 fake-ip 由前端 mask 函数遮罩，
  数据明文下发到浏览器。只有 preferred networks 做到了后端不返回。P2 做「报告脱敏」时
  统一搬运到后端。
