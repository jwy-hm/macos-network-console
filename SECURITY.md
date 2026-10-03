# 安全政策

## 报告漏洞

如发现安全漏洞，请通过 **GitHub Security Advisory** 私密报告，**不要**开公开 issue。

- 提交入口：本仓库 `Security` 标签页 → `Report a vulnerability`
- 我们会在 **48 小时内**回复

## 安全设计

本工具纯本地运行，只监听 `127.0.0.1`，不接受来自本机以外的请求。核心安全基线：

- CSRF token 校验（进程启动生成一次）
- 命令白名单 + 黑名单（拒绝 `sudo` / `sh` / `python` 等万能命令）
- 安全响应头（CSP / nosniff / no-referrer / X-Frame-Options）
- 请求体大小上限

详见 [docs/PRIVACY.md](docs/PRIVACY.md) 与源码注释。
