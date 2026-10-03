"""系统状态检测。

8 项检查并行执行（子进程并发），整体超时上限 8s。
所有判定通用化：只遍历配置表与关键词，不写死任何具体客户端名 / 设备名 / IP。
契约：``hint`` 仅在 ``ok=False`` 时返回。
"""

from __future__ import annotations

import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from network_console import config
from network_console.core import platform_macos
from network_console.core.shell import Result


def _check(check_id: str, label: str, ok: bool, value: str, hint: str = "") -> Dict:
    item: Dict = {"id": check_id, "label": label, "ok": ok, "value": value}
    if not ok and hint:
        item["hint"] = hint
    return item


def _collect() -> Dict[str, Result]:
    """并行采集原始数据。Wi-Fi 详情（system_profiler）单独走慢接口，不进主环。"""
    jobs = {
        "ps": platform_macos.ps,
        "lsof": platform_macos.lsof_listen,
        "proxy": platform_macos.scutil_proxy,
        "external": lambda: platform_macos.curl_http(config.EXTERNAL_PROBE_URLS[0]),
        "routes": platform_macos.netstat_rn,
        "dns": platform_macos.scutil_dns,
        "tailscale": platform_macos.tailscale_status,
        "route": platform_macos.default_route,
    }
    results: Dict[str, Result] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {key: ex.submit(fn) for key, fn in jobs.items()}
        for key, fut in futures.items():
            try:
                results[key] = fut.result(timeout=8)
            except Exception:
                results[key] = Result(ok=False, error="检测失败或超时")
    return results


# ---------- 纯解析函数（可单测） ----------

def _running_clients(ps_text: str, kinds: Optional[List[str]] = None) -> List[str]:
    """从进程表匹配运行中的客户端；kinds 为 None 表示不限类型。"""
    ps_lower = ps_text.lower()
    names: List[str] = []
    for client in config.PROXY_CLIENTS:
        if kinds is not None and client["kind"] not in kinds:
            continue
        if any(kw in ps_lower for kw in client["keywords"]):
            names.append(str(client["name"]))
    return names


def _listening_ports(lsof_text: str) -> set:
    ports = set()
    for line in lsof_text.splitlines():
        for part in line.split():
            if ":" in part:
                port = part.rsplit(":", 1)[-1]
                if port.isdigit():
                    ports.add(int(port))
    return ports


def _system_proxy_enabled(proxy_text: str) -> bool:
    return any("%s : 1" % key in proxy_text for key in ("HTTPEnable", "HTTPSEnable", "SOCKSEnable"))


def _count_10064_routes(routes_text: str) -> int:
    return sum(1 for line in routes_text.splitlines() if "100.64" in line)


def _parse_nameservers(dns_text: str) -> List[str]:
    servers: List[str] = []
    for line in dns_text.splitlines():
        line = line.strip()
        if line.startswith("nameserver["):
            value = line.split(":", 1)[1].strip() if ":" in line else ""
            if value and value not in servers:
                servers.append(value)
    return servers


def _count_peers(tailscale_text: str) -> int:
    text = tailscale_text.strip()
    if not text or "stopped" in text.lower():
        return 0
    return len([ln for ln in text.splitlines() if ln.strip()])


def _parse_default_route(route_text: str) -> tuple:
    gateway = interface = ""
    for line in route_text.splitlines():
        line = line.strip()
        if line.startswith("gateway:"):
            gateway = line.split(":", 1)[1].strip()
        elif line.startswith("interface:"):
            interface = line.split(":", 1)[1].strip()
    return gateway, interface


# ---------- 8 项检查 ----------

def check_proxy(data: Dict[str, Result]) -> Dict:
    names = _running_clients(data.get("ps", Result(ok=False)).value, kinds=["proxy"])
    if names:
        return _check("proxy", "代理客户端", True, "运行中：" + "、".join(names))
    ports = _listening_ports(data.get("lsof", Result(ok=False)).value)
    hit = [p for p in config.COMMON_PROXY_PORTS if p in ports]
    if hit:
        return _check("proxy", "代理客户端", True, "监听端口：" + ",".join(str(p) for p in hit))
    if _system_proxy_enabled(data.get("proxy", Result(ok=False)).value):
        return _check("proxy", "代理客户端", True, "系统代理已启用（未识别客户端）")
    return _check("proxy", "代理客户端", False, "未检测到代理", "请在菜单栏或系统设置中启动代理客户端")


def check_mesh(data: Dict[str, Result]) -> Dict:
    names = _running_clients(data.get("ps", Result(ok=False)).value, kinds=["mesh", "vpn", "zero-trust"])
    if names:
        return _check("mesh", "内网互联", True, "运行中：" + "、".join(names))
    return _check("mesh", "内网互联", False, "未运行", "使用内网互联（Tailscale/ZeroTier/WireGuard）时才需要")


def check_external(data: Dict[str, Result]) -> Dict:
    value = data.get("external", Result(ok=False)).value
    code = value.split()[0] if value else "000"
    ok = code == "200"
    return _check("external", "外网连通性", ok,
                  "正常" if ok else "失败（HTTP %s）" % code,
                  "外网不可达，可能是代理或 DNS 问题")


def check_route_conflict(data: Dict[str, Result]) -> Dict:
    count = _count_10064_routes(data.get("routes", Result(ok=False)).value)
    conflict = count >= 2
    return _check("route_conflict", "路由冲突", not conflict,
                  "无冲突" if not conflict else "检测到 100.64/10 冲突",
                  "与 VPN/内网隧道撞段，见路由表" if conflict else "")


def check_dns(data: Dict[str, Result]) -> Dict:
    servers = _parse_nameservers(data.get("dns", Result(ok=False)).value)
    if servers:
        return _check("dns", "DNS 解析", True, "、".join(servers[:3]))
    return _check("dns", "DNS 解析", False, "未获取到 DNS")


def check_internal_peers(data: Dict[str, Result]) -> Dict:
    peers = _count_peers(data.get("tailscale", Result(ok=False)).value)
    if peers:
        return _check("internal", "内网设备", True, "%d 台在线" % peers)
    return _check("internal", "内网设备", False, "无在线设备", "确认已登录并连接内网互联工具")


def check_proxy_port(data: Dict[str, Result]) -> Dict:
    ports = _listening_ports(data.get("lsof", Result(ok=False)).value)
    hit = [p for p in config.COMMON_PROXY_PORTS if p in ports]
    if hit:
        return _check("proxy_port", "代理监听端口", True, ",".join(str(p) for p in hit))
    return _check("proxy_port", "代理监听端口", False, "未发现常见代理端口")


def check_default_route(data: Dict[str, Result]) -> Dict:
    gateway, interface = _parse_default_route(data.get("route", Result(ok=False)).value)
    if gateway or interface:
        return _check("default_route", "默认路由", True, "接口 %s，网关 %s" % (interface or "-", gateway or "-"))
    return _check("default_route", "默认路由", False, "未获取到")


def get_status() -> Dict:
    """并行执行 8 项检测，返回结构化结果。"""
    data = _collect()
    checks = [
        check_proxy(data),
        check_mesh(data),
        check_external(data),
        check_route_conflict(data),
        check_dns(data),
        check_internal_peers(data),
        check_proxy_port(data),
        check_default_route(data),
    ]
    return {"checks": checks, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
