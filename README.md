# macos-network-console

![CI](https://github.com/jwy-hm/macos-network-console/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-10b981)

一个纯本地的 macOS 网络管理控制台：在浏览器里查看本机的 Wi-Fi、网络接口、DNS、代理、路由、连接与网络诊断。

- **零运行时依赖**：后端只用 Python 标准库，前端单页 HTML，无构建步骤。
- **纯本地**：只监听 `127.0.0.1`，不上传、不收集、不写日志（默认）。
- **双击即用**：`clone` 后双击启动脚本即可。

## 系统要求

- macOS
- 系统自带 `python3`（≥ 3.9）

## 快速开始

```bash
git clone <repo-url>
cd macos-network-console
# 双击 scripts/launch.command，或：
python3 -m network_console
```

浏览器会自动打开 `http://127.0.0.1:8777`（端口被占用会自动 +1，或用 `--port` 指定）。

## 功能

- **总览**：代理客户端、内网互联（Tailscale/ZeroTier 等）、外网连通性、路由冲突、DNS、默认路由，8 项并行检测。
- **网络接口**：接口状态、IP、MAC、MTU 与收发流量。
- **连接**：列出当前进程的网络连接，支持按进程名 / 端口过滤。
- **诊断**：ping、traceroute、HTTP 头时间分解、DNS 解析，结果就地留存。

## 环境提示（代理 / VPN 下的已知行为）

诊断功能直接调用系统命令。当本机开启了代理 / VPN 的 **TUN 全局模式**（如 Clash、Surge、Shadowrocket 的 TUN 模式）时，以下结果是**正常现象**，并非工具故障：

- **traceroute 全部显示 `*`（超时）**：TUN 模式会拦截 ICMP 探测包，逐跳探测得不到响应。关闭代理或切换到非 TUN 模式后即可看到真实路由。
- **DNS 解析返回 `198.18.0.x` 这类地址**：这是代理软件的 fake-ip 段（RFC 2544 保留网段），并非目标域名的真实 IP。
- **外网连通性检测**：默认目标为 google.com / cloudflare.com，检测结果反映本机真实可达性。

## 开发

```bash
make dev      # 建 venv 并安装 ruff + pytest
make lint     # 代码规范检查
make test     # 单元测试
make privacy-check   # 隐私自查
```

## 隐私

见 [docs/PRIVACY.md](docs/PRIVACY.md)。

## 安全

见 [SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE)
