"""macOS 平台命令封装。

所有命令统一走 ``core.shell.run``（列表参数、白名单、超时），返回结构化 Result。
api 层不直接触碰 shell；未来扩展其它平台时新增 platform_*.py 即可。
"""

from __future__ import annotations

from network_console.core import shell
from network_console.core.shell import Result

# networksetup -get* 的子命令映射（只读）
_PROXY_FLAGS = {
    "http": "-getwebproxy",
    "https": "-getsecurewebproxy",
    "socks": "-getsocksfirewallproxy",
}


def ifconfig() -> Result:
    """所有网络接口配置。"""
    return shell.run(["ifconfig"])


def netstat_ib() -> Result:
    """每接口收发字节统计（Ibytes/Obytes）。"""
    return shell.run(["netstat", "-ib"])


def default_route() -> Result:
    """默认路由（gateway + interface）。"""
    return shell.run(["route", "-n", "get", "default"])


def ps() -> Result:
    """进程列表（用于客户端检测）。"""
    return shell.run(["ps", "aux"])


def scutil_dns() -> Result:
    """当前 DNS 解析配置。"""
    return shell.run(["scutil", "--dns"])


def networksetup_list_services() -> Result:
    """网络服务列表（Wi-Fi / 以太网等）。"""
    return shell.run(["networksetup", "-listallnetworkservices"])


def networksetup_get_proxy(service: str, kind: str) -> Result:
    """读取某个网络服务的系统代理设置（http/https/socks）。"""
    flag = _PROXY_FLAGS.get(kind)
    if flag is None:
        return Result(ok=False, error="未知代理类型", hint=kind)
    return shell.run(["networksetup", flag, service])


def system_profiler_wifi() -> Result:
    """Wi-Fi 详情（较慢，建议异步加载）。"""
    return shell.run(["system_profiler", "SPAirPortDataType"])


def tailscale_status() -> Result:
    """Tailscale 状态（节点列表）。"""
    return shell.run(["tailscale", "status"])


def lsof_listen() -> Result:
    """监听中的 TCP 端口。"""
    return shell.run(["lsof", "-iTCP", "-sTCP:LISTEN", "-n", "-P"])


def ping(host: str, count: int = 1, timeout_ms: int = 3000) -> Result:
    """BSD ping：-c 次数，-W 单包超时毫秒。"""
    return shell.run(["ping", "-c", str(count), "-W", str(timeout_ms), host])


def curl_http(url: str) -> Result:
    """HTTP 连通性探测，返回 "状态码 总耗时秒"。"""
    return shell.run(
        ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code} %{time_total}", "--max-time", "8", url]
    )
