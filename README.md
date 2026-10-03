[**English**](README.md) | [简体中文](README.zh-CN.md)

# macos-network-console

![CI](https://github.com/jwy-hm/macos-network-console/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-10b981)

A purely-local macOS network management console: inspect Wi-Fi, network interfaces, DNS, proxies, routes, connections, and run diagnostics — all in your browser.

- **Zero runtime dependencies**: backend uses only the Python standard library; the frontend is a single-page HTML app with no build step.
- **Purely local**: listens on `127.0.0.1` only. No uploads, no telemetry, no logs (by default).
- **Double-click to run**: clone, then double-click the launcher.

## Requirements

- macOS
- System `python3` (≥ 3.9)

## Quick start

```bash
git clone <repo-url>
cd macos-network-console
# Double-click scripts/launch.command, or:
python3 -m network_console
```

Your browser opens `http://127.0.0.1:8777` automatically (the port auto-increments if taken, or pass `--port`).

## Features

- **Overview**: proxy clients, mesh/VPN (Tailscale/ZeroTier etc.), external connectivity, route conflicts, DNS, default route — 8 parallel checks.
- **Interfaces**: status, IP, MAC, MTU, and RX/TX traffic.
- **Connections**: current process connections, filterable by process name / port.
- **Diagnostics**: ping, traceroute, HTTP timing breakdown, DNS lookup, results kept locally.

## Known behavior under proxy / VPN (TUN mode)

Diagnostics invoke system commands directly. When a **global TUN-mode proxy/VPN** is active (Clash, Surge, Shadowrocket TUN, etc.), the following are **expected**, not bugs:

- **traceroute shows all `*` (timeouts)**: TUN mode drops ICMP probes, so per-hop resolution fails. Turn the proxy off or switch to non-TUN mode to see the real route.
- **DNS returns addresses like `198.18.0.x`**: this is the proxy's fake-ip range (RFC 2544 reserved), not the real IP of the domain.
- **External connectivity check**: default targets are google.com / cloudflare.com; results reflect the machine's actual reachability.

## Development

```bash
make dev      # create venv and install ruff + pytest
make lint     # lint
make test     # unit tests
make privacy-check   # privacy self-check
```

## Privacy

See [docs/PRIVACY.md](docs/PRIVACY.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
