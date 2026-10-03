"""全局配置。所有值均可被环境变量覆盖，不含任何私人标识。"""

from __future__ import annotations

import os
from typing import Dict, List

# 服务端口（默认 8777，被占用时自动 +1；可用 --port 显式指定）
PORT = int(os.environ.get("NETWORK_CONSOLE_PORT", "8777"))

# 用户数据目录（本地配置 + 备份，不放进版本库）
DATA_DIR = os.path.expanduser(
    os.environ.get("NETWORK_CONSOLE_DATA_DIR", "~/.config/macos-network-console")
)
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
LOCAL_CONFIG_PATH = os.path.join(DATA_DIR, "local.json")

# 网络客户端检测表：进程关键词 + 常见安装路径（均为通用值，可扩展）
# kind: proxy / vpn / mesh / zero-trust
PROXY_CLIENTS: List[Dict[str, object]] = [
    {
        "name": "Shadowrocket",
        "kind": "proxy",
        "keywords": ["shadowrocket", "macpackettunnel"],
        "paths": ["/Applications/Shadowrocket.app"],
    },
    {
        "name": "Clash / ClashX / Clash Verge",
        "kind": "proxy",
        "keywords": ["clash", "clashx", "mihomo"],
        "paths": [
            "/Applications/ClashX.app",
            "/Applications/ClashX Pro.app",
            "/Applications/Clash Verge.app",
        ],
    },
    {
        "name": "Surge",
        "kind": "proxy",
        "keywords": ["surge"],
        "paths": ["/Applications/Surge.app"],
    },
    {
        "name": "sing-box / Xray / V2Ray",
        "kind": "proxy",
        "keywords": ["sing-box", "xray", "v2ray"],
        "paths": [],
    },
    {
        "name": "WireGuard",
        "kind": "vpn",
        "keywords": ["wireguard"],
        "paths": ["/Applications/WireGuard.app"],
    },
    {
        "name": "OpenVPN / Tunnelblick",
        "kind": "vpn",
        "keywords": ["openvpn", "tunnelblick"],
        "paths": ["/Applications/Tunnelblick.app", "/Applications/OpenVPN Connect.app"],
    },
    {
        "name": "Tailscale",
        "kind": "mesh",
        "keywords": ["tailscale", "tailscaled"],
        "paths": ["/Applications/Tailscale.app"],
    },
    {
        "name": "ZeroTier",
        "kind": "mesh",
        "keywords": ["zerotier"],
        "paths": ["/Applications/ZeroTier One.app"],
    },
    {
        "name": "Sangfor aTrust",
        "kind": "zero-trust",
        "keywords": ["atrust"],
        "paths": ["/Applications/aTrust.app"],
    },
]

# 常见代理监听端口（端口扫描用）
COMMON_PROXY_PORTS: List[int] = [1080, 1087, 7890, 7891, 7897, 8888, 6152, 9090]

# 外网连通性检测默认目标（用户可改）
EXTERNAL_PROBE_URLS: List[str] = [
    "https://www.google.com",
    "https://www.cloudflare.com",
]

# 测速延迟阈值（毫秒）
LATENCY_FAST_MS = 500
LATENCY_SLOW_MS = 2000

# HTTP 请求体上限（防超大 body 打爆本地服务）
MAX_BODY_BYTES = 1024 * 1024

# 连接监控：最多返回的连接条数（超出截断，前端据 truncated 提示）
MAX_CONNECTIONS = int(os.environ.get("NETWORK_CONSOLE_MAX_CONNECTIONS", "300"))

# 诊断工具统一超时（秒）：ping / traceroute / HTTP 都可能跑 10s+，前端 + 后端都压在这里
DIAG_TIMEOUT = float(os.environ.get("NETWORK_CONSOLE_DIAG_TIMEOUT", "15"))

# ping 诊断默认参数（BSD）
PING_COUNT = 5
PING_INTERVAL = 0.2
PING_TIMEOUT_MS = 3000

# traceroute 参数：-w 每跳超时秒 / -q 每跳探测数 / -m 最大跳数
TRACEROUTE_MAX_HOPS = 20
