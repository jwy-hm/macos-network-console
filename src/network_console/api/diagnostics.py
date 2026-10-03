"""诊断工具箱：ping / traceroute / HTTP 头分解 / DNS 解析。

- 能力探测（``probe_tools``）在首次调用时检查各命令是否在 PATH，结果缓存到进程内存。
- 每个工具返回统一结构：``{ok, tool, target, summary, detail, raw}``，异常时附带 ``warning`` 码。
- 所有命令走 ``core.platform_macos``（白名单 + 超时），超时按工具区分（``config.TOOL_TIMEOUTS``）。
"""

from __future__ import annotations

import ipaddress
import re
import shutil
from typing import Dict, List, Optional

from network_console import config
from network_console.core import platform_macos

# 能力探测清单（均为只读诊断命令，已在 shell 白名单内）
_TOOLS = ["ping", "traceroute", "curl", "dig", "nslookup", "openssl", "nc"]

# 进程级缓存：只探一次
_tools_cache: Optional[Dict[str, bool]] = None

# ping 统计行
_PING_TX = re.compile(r"(\d+) packets transmitted, (\d+) (?:packets )?received")
_PING_LOSS = re.compile(r"([\d.]+)% packet loss")
_PING_RTT = re.compile(
    r"round-trip min/avg/max/stddev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)"
)

# 代理 fake-ip 保留段（RFC 2544 的 198.18/15 + 保留的 240/4）
_FAKE_IP_NETWORKS = [
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("240.0.0.0/4"),
]


def is_fake_ip(value: str) -> bool:
    """判断字符串是否落在代理 fake-ip 保留段（非 IP 一律 False）。"""
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return any(ip in net for net in _FAKE_IP_NETWORKS)


def probe_tools() -> Dict[str, bool]:
    """检查诊断命令是否可用，结果缓存（启动后只探一次）。"""
    global _tools_cache
    if _tools_cache is None:
        _tools_cache = {t: shutil.which(t) is not None for t in _TOOLS}
    return dict(_tools_cache)


def get_tools() -> Dict:
    """能力探测接口：返回工具可用性 + 每工具超时（前端据此设 AbortController 上限）。"""
    return {"ok": True, "tools": probe_tools(), "timeouts": config.TOOL_TIMEOUTS}


# ---------- 纯解析函数（可单测） ----------

def parse_ping(text: str) -> Dict:
    """解析 BSD ping 末尾统计行（丢包率 + RTT）。"""
    tx = rx = None
    loss = None
    rtt: Dict[str, float] = {}
    for line in text.splitlines():
        m = _PING_TX.search(line)
        if m:
            tx, rx = int(m.group(1)), int(m.group(2))
        m = _PING_LOSS.search(line)
        if m:
            loss = float(m.group(1))
        m = _PING_RTT.search(line)
        if m:
            rtt = {
                "min": float(m.group(1)),
                "avg": float(m.group(2)),
                "max": float(m.group(3)),
                "stddev": float(m.group(4)),
            }
    return {"transmitted": tx, "received": rx, "loss": loss, "rtt": rtt}


def parse_traceroute(text: str) -> List[Dict]:
    """解析 ``traceroute -n -q 1`` 输出为跳数列表。"""
    hops: List[Dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"^\s*(\d+)\s+(.*)$", line)
        if not m:
            continue
        hop = int(m.group(1))
        tokens = m.group(2).split()
        addr = ""
        if tokens and tokens[0] != "*":
            addr = tokens[0]
        # 时间形如 "2.123 ms"，用正则整体抓，避免把 "ms" 拆成独立 token
        times: List[float] = [float(t) for t in re.findall(r"([\d.]+) ms", m.group(2))]
        hops.append({"hop": hop, "addr": addr, "time_ms": times})
    return hops


def parse_curl_timing(text: str) -> Dict:
    """分离 HTTP 响应头与时间分解，提取最终状态码 + 各阶段耗时。"""
    headers_part, timing_part = text, ""
    if "---TIMING---" in text:
        headers_part, timing_part = text.split("---TIMING---", 1)
    status = ""
    status_count = 0
    for line in headers_part.splitlines():
        if line.startswith("HTTP/"):
            status = line.strip()
            status_count += 1
    timing: Dict[str, str] = {}
    for line in timing_part.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key in ("namelookup", "connect", "appconnect", "starttransfer", "total"):
                timing[key] = value
    return {
        "status": status,
        "redirects": max(0, status_count - 1),
        "timing": timing,
        "headers": headers_part,
    }


# ---------- 工具执行 ----------

def _run_ping(target: str) -> Dict:
    timeout = config.TOOL_TIMEOUTS.get("ping", config.DIAG_TIMEOUT)
    res = platform_macos.ping_diag(
        target, count=config.PING_COUNT, interval=config.PING_INTERVAL,
        timeout_ms=config.PING_TIMEOUT_MS, timeout=timeout,
    )
    stats = parse_ping(res.value)
    loss = stats.get("loss")
    ok = loss == 0.0
    rtt = stats.get("rtt") or {}
    summary = "丢包 %s%%" % loss if loss is not None else "无统计"
    if rtt.get("avg") is not None:
        summary += "，平均 %.1f ms" % rtt["avg"]
    return {"ok": ok, "tool": "ping", "target": target, "summary": summary, "detail": stats, "raw": res.value}


def _run_traceroute(target: str) -> Dict:
    timeout = config.TOOL_TIMEOUTS.get("traceroute", config.TRACEROUTE_TIMEOUT)
    res = platform_macos.traceroute_diag(target, max_hops=config.TRACEROUTE_MAX_HOPS, timeout=timeout)
    hops = parse_traceroute(res.value)
    summary = "共 %d 跳" % len(hops) if hops else "无结果"
    result = {"ok": bool(hops), "tool": "traceroute", "target": target, "summary": summary, "detail": {"hops": hops}, "raw": res.value}
    # 所有跳点都超时（TUN 代理拦截 ICMP 的典型表现）→ 提示
    if hops and all(not h["addr"] for h in hops):
        result["warning"] = "all_hops_timeout"
    return result


def _run_http(target: str) -> Dict:
    timeout = config.TOOL_TIMEOUTS.get("http", config.DIAG_TIMEOUT)
    res = platform_macos.curl_timing(target, max_time=int(timeout), timeout=timeout)
    parsed = parse_curl_timing(res.value)
    timing = parsed["timing"]
    status = parsed["status"]
    ok = bool(status) and status.split()[1][0] in ("2", "3") if len(status.split()) > 1 else False
    summary = status or "无响应"
    if timing.get("total"):
        summary += "，总耗时 %ss" % timing["total"]
    return {"ok": ok, "tool": "http", "target": target, "summary": summary, "detail": parsed, "raw": res.value}


def _run_dns(target: str) -> Dict:
    timeout = config.TOOL_TIMEOUTS.get("dns", config.DIAG_TIMEOUT)
    if probe_tools().get("dig"):
        res = platform_macos.dig_lookup(target, timeout=timeout)
    else:
        res = platform_macos.nslookup_host(target, timeout=timeout)
    records = [ln.strip() for ln in res.value.splitlines() if ln.strip()]
    ok = bool(records) and not res.error
    summary = "、".join(records[:8]) if records else "无记录"
    result = {"ok": ok, "tool": "dns", "target": target, "summary": summary, "detail": {"records": records}, "raw": res.value}
    # 解析结果落在 fake-ip 段 → 提示（代理软件正常行为，非真实 IP）
    if any(is_fake_ip(r) for r in records):
        result["warning"] = "fake_ip"
    return result


_RUNNERS = {
    "ping": _run_ping,
    "traceroute": _run_traceroute,
    "http": _run_http,
    "dns": _run_dns,
}


def run_tool(tool: str, target: str) -> Dict:
    """执行某个诊断工具。未知工具 / 空目标返回错误。"""
    target = (target or "").strip()
    if not target:
        return {"ok": False, "error": "缺少目标"}
    # 防选项注入：target 以 "-" 开头会被 ping/traceroute/dig 当参数解析
    if target.startswith("-"):
        return {"ok": False, "error": "非法目标"}
    # HTTP 工具只允许 http/https，避免 file:// 等 scheme 读取本地文件
    if tool == "http" and not (target.startswith("http://") or target.startswith("https://")):
        return {"ok": False, "error": "HTTP 工具仅支持 http/https"}
    runner = _RUNNERS.get(tool)
    if runner is None:
        return {"ok": False, "error": "未知工具：%s" % (tool or "?")}
    return runner(target)
