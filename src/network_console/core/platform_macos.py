"""macOS 平台命令封装。

所有命令统一走 ``core.shell.run``（列表参数、白名单、超时），返回结构化 Result。
api 层不直接触碰 shell；未来扩展其它平台时新增 platform_*.py 即可。
"""

from __future__ import annotations

from network_console import config
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


def scutil_proxy() -> Result:
    """系统代理设置（HTTPEnable / SOCKSEnable 等）。"""
    return shell.run(["scutil", "--proxy"])


def netstat_rn() -> Result:
    """路由表。"""
    return shell.run(["netstat", "-rn"])


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


def lsof_connections() -> Result:
    """当前所有网络连接（含非监听）。-i=网络文件 -n=不解析主机名 -P=不解析端口名，省 3-5 秒解析。"""
    return shell.run(["lsof", "-i", "-n", "-P"])


def ping(host: str, count: int = 1, timeout_ms: int = 3000) -> Result:
    """BSD ping：-c 次数，-W 单包超时毫秒。"""
    return shell.run(["ping", "-c", str(count), "-W", str(timeout_ms), host])


def ping_diag(host: str, count: int = 5, interval: float = 0.2, timeout_ms: int = 3000) -> Result:
    """诊断用 ping：-c 次数 -i 间隔秒 -W 单包超时毫秒。"""
    return shell.run(
        ["ping", "-c", str(count), "-i", str(interval), "-W", str(timeout_ms), host],
        timeout=config.DIAG_TIMEOUT,
    )


def traceroute_diag(host: str, max_hops: int = 20) -> Result:
    """诊断用 traceroute：-n 不反查 DNS、-w 每跳超时 2s、-q 每跳 1 次、-m 最大跳数。"""
    return shell.run(
        ["traceroute", "-n", "-w", "2", "-q", "1", "-m", str(max_hops), host],
        timeout=config.DIAG_TIMEOUT,
    )


def curl_http(url: str) -> Result:
    """HTTP 连通性探测，返回 "状态码 总耗时秒"。"""
    return shell.run(
        ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code} %{time_total}", "--max-time", "8", url]
    )


def curl_timing(url: str, max_time: int = 15) -> Result:
    """HTTP 头 + 时间分解一次拿到：-D - 输出响应头，-w 输出各阶段耗时。"""
    wfmt = (
        "---TIMING---\\n"
        "namelookup:%{time_namelookup}\\n"
        "connect:%{time_connect}\\n"
        "appconnect:%{time_appconnect}\\n"
        "starttransfer:%{time_starttransfer}\\n"
        "total:%{time_total}\\n"
    )
    return shell.run(
        [
            "curl", "-sS", "-L", "--max-redirs", "5",
            "-o", "/dev/null", "-D", "-", "-w", wfmt,
            "--max-time", str(max_time), url,
        ],
        timeout=config.DIAG_TIMEOUT,
    )


def dig_lookup(domain: str) -> Result:
    """DNS 解析（A 记录等）。"""
    return shell.run(["dig", "+short", domain])


def nslookup_host(domain: str) -> Result:
    """DNS 解析（dig 不可用时的回退）。"""
    return shell.run(["nslookup", domain])
