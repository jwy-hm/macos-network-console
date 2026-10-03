"""网络接口总览：接口列表 + 收发流量 + 默认网关。"""

from __future__ import annotations

import re
from typing import Dict, List

from network_console.core import platform_macos


def parse_netstat_ib(text: str) -> List[Dict]:
    """解析 ``netstat -ib``。

    BSD 输出同一接口会重复多行（link 层一行、v4 一行、v6 一行），
    按 Name 分组后取 Ibytes/Obytes 最大值那行的数值。
    """
    interfaces: Dict[str, Dict] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 10 or parts[0] == "Name":
            continue
        name = parts[0]
        try:
            mtu = parts[1]
            ibytes = int(parts[6])
            obytes = int(parts[9])
        except (ValueError, IndexError):
            continue
        cur = interfaces.setdefault(name, {"name": name, "mtu": mtu, "ibytes": 0, "obytes": 0})
        cur["ibytes"] = max(cur["ibytes"], ibytes)
        cur["obytes"] = max(cur["obytes"], obytes)
        # link 层行带有 MAC（形如 aa:bb:...，且不含点分十进制 IP）
        addr = parts[3] if len(parts) > 3 else ""
        if "mac" not in cur and ":" in addr and not re.search(r"\d+\.\d+\.\d+\.\d+", addr):
            cur["mac"] = addr
    return sorted(interfaces.values(), key=lambda x: x["name"])


def parse_ifconfig(text: str) -> List[Dict]:
    """解析 ``ifconfig``，提取每接口的 MTU / IPv4 / IPv6 / MAC / 状态。"""
    interfaces: Dict[str, Dict] = {}
    current: Dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line[0] not in (" ", "\t"):
            if ":" not in line:
                continue
            name = line.split(":", 1)[0].strip()
            current = {"name": name, "mtu": None, "inet": None, "inet6": None, "mac": None, "up": "UP" in line}
            interfaces[name] = current
            m = re.search(r"mtu (\d+)", line)
            if m:
                current["mtu"] = m.group(1)
        elif current is not None:
            line = line.strip()
            if line.startswith("ether "):
                current["mac"] = line.split()[1]
            elif line.startswith("inet "):
                current["inet"] = line.split()[1]
            elif line.startswith("inet6 ") and "::" in line:
                current["inet6"] = line.split()[1].split("%")[0]
    return sorted(interfaces.values(), key=lambda x: x["name"])


def _parse_default_route(text: str) -> Dict:
    gateway = interface = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("gateway:"):
            gateway = line.split(":", 1)[1].strip()
        elif line.startswith("interface:"):
            interface = line.split(":", 1)[1].strip()
    return {"gateway": gateway, "interface": interface}


def get_interfaces() -> Dict:
    """合并 ifconfig 与 netstat -ib，返回接口总览。"""
    ifc = platform_macos.ifconfig()
    traffic = platform_macos.netstat_ib()
    route = platform_macos.default_route()

    interfaces = parse_ifconfig(ifc.value)
    traffic_map = {t["name"]: t for t in parse_netstat_ib(traffic.value)}

    for item in interfaces:
        t = traffic_map.get(item["name"])
        if t:
            item["ibytes"] = t["ibytes"]
            item["obytes"] = t["obytes"]
            if not item.get("mac"):
                item["mac"] = t.get("mac")
        else:
            item["ibytes"] = 0
            item["obytes"] = 0

    return {
        "ok": True,
        "interfaces": interfaces,
        "default_route": _parse_default_route(route.value),
    }
