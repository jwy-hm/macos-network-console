"""DNS 概览与查询。

概览（GET /api/dns）：
- 解析 ``scutil --dns`` 的多 resolver 结构（主段 + scoped 段）
- 每条 resolver 给出「这意味着什么」的解读：fake-ip（代理接管）、
  mDNS 本地域、真实运营商/公共 DNS 等
- 只陈述事实，不判定对错（不承诺「DNS 泄漏检测」）

查询（POST /api/dns/query）：
- 指定记录类型（A/AAAA/CNAME/MX/TXT/NS），走 dig +short

注意：DNS 切换（networksetup -setdnsservers）需要管理员权限，P1-02 不做。
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from network_console.core import platform_macos

# 记录类型白名单：dig 支持且常见
_RECORD_TYPES = ("A", "AAAA", "CNAME", "MX", "TXT", "NS")

# fake-ip 段（代理软件用于「劫持」DNS 返回的保留地址，非真实 IP）
_FAKE_IP_RE = re.compile(r"^(198\.18\.|198\.19\.)")


def _interpret(resolver: Dict) -> str:
    """根据 resolver 的 nameserver / domain / options 给出解读。"""
    servers = resolver.get("nameservers", [])
    domain = resolver.get("domain", "")
    options = resolver.get("options", "")

    if servers and any(_FAKE_IP_RE.match(s) for s in servers):
        return "代理软件的 fake-ip 段，DNS 查询被代理客户端（如 Shadowrocket/Clash）接管"
    if domain == "local" or "mdns" in options:
        return "mDNS 本地服务解析（局域网设备发现），非公网 DNS"
    if domain.endswith("in-addr.arpa") or domain.endswith("ip6.arpa"):
        return "反向解析域（IP → 域名），mDNS 使用"
    if servers:
        return "实际生效的 DNS 服务器（" + "、".join(servers) + "）"
    if not servers:
        return "未配置 DNS 服务器"
    return ""


def _parse_scutil_dns(text: str) -> List[Dict]:
    """解析 scutil --dns 输出为 resolver 列表，区分主段与 scoped 段。"""
    resolvers: List[Dict] = []
    current: Optional[Dict] = None
    section = "main"

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "DNS configuration (for scoped queries)":
            if current:
                resolvers.append(current)
                current = None
            section = "scoped"
            continue
        if stripped.startswith("resolver #"):
            if current:
                resolvers.append(current)
            current = {"section": section, "nameservers": [], "domain": "", "options": "", "if_index": "", "reach": ""}
            continue
        if current is None:
            continue
        if stripped.startswith("nameserver["):
            value = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            if value:
                current["nameservers"].append(value)
        elif stripped.startswith("domain   :"):
            current["domain"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("options  :"):
            current["options"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("if_index :"):
            current["if_index"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("reach    :"):
            current["reach"] = stripped.split(":", 1)[1].strip()

    if current:
        resolvers.append(current)

    # 补充解读
    for r in resolvers:
        r["meaning"] = _interpret(r)
    return resolvers


def _parse_service_dns(value: str) -> List[str]:
    """解析 networksetup -getdnsservers 输出为 DNS 列表。"""
    servers: List[str] = []
    for line in value.splitlines():
        line = line.strip()
        if not line or line.startswith("There aren't"):
            continue
        servers.append(line)
    return servers


def get_dns_overview() -> Dict:
    """GET /api/dns：概览（scutil 多 resolver + 各服务的 DNS 设置）。"""
    scutil_res = platform_macos.scutil_dns()
    resolvers = _parse_scutil_dns(scutil_res.value) if scutil_res.ok else []

    services_res = platform_macos.networksetup_list_services()
    services: List[Dict] = []
    if services_res.ok:
        for line in services_res.value.splitlines():
            line = line.strip()
            if not line or line.startswith("An asterisk") or line.startswith("*"):
                continue
            dns_res = platform_macos.networksetup_get_dns(line)
            servers = _parse_service_dns(dns_res.value) if dns_res.ok else []
            services.append({
                "service": line,
                "servers": servers,
                "meaning": "该网络服务配置的 DNS" if servers else "该网络服务未单独配置 DNS（走系统默认）",
            })

    return {"ok": True, "resolvers": resolvers, "services": services}


def query_dns(domain: str, record_type: str = "A") -> Dict:
    """POST /api/dns/query：指定记录类型查询。"""
    rt = record_type.upper() if record_type else "A"
    if rt not in _RECORD_TYPES:
        return {"ok": False, "error": "不支持的记录类型：%s" % rt, "results": []}
    # 域名简单校验（防命令注入——dig 走列表参数，但 domain 仍要净化）
    domain = (domain or "").strip()
    if not domain or any(ch in domain for ch in " ;&|`$<>\\\n\r"):
        return {"ok": False, "error": "域名不合法", "results": []}
    res = platform_macos.dig_query(domain, rt)
    if not res.ok:
        return {"ok": False, "error": res.error or "查询失败", "results": []}
    results = [ln for ln in (res.value or "").splitlines() if ln.strip()]
    return {"ok": True, "domain": domain, "type": rt, "results": results}
