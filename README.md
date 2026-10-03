# macos-network-console

一个纯本地的 macOS 网络管理控制台：在浏览器里查看和管理本机的 Wi-Fi、网络接口、DNS、代理、路由、连接与网络诊断。

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

## 开发

```bash
make dev      # 建 venv 并安装 ruff + pytest
make lint     # 代码规范检查
make test     # 单元测试
make privacy-check   # 隐私自查
```

## 隐私

见 [docs/PRIVACY.md](docs/PRIVACY.md)。

## License

[MIT](LICENSE)
