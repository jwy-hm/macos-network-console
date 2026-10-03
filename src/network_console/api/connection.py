"""连接监控：列出当前进程的网络连接。

数据来源 ``lsof -i -n -P``（普通用户，无 sudo）——只能看到当前用户进程的连接，
系统级连接需 sudo。返回结构带 ``scope`` 标注，前端据此提示权限边界。
"""

from __future__ import annotations

import re
from typing import Dict, List

from network_console import config
from network_console.core import platform_macos

# 匹配 lsof NAME 字段里的连接状态，如 "(ESTABLISHED)" / "(LISTEN)"
_STATE_RE = re.compile(r"\(([A-Z_]+)\)")


def parse_lsof(text: str) -> List[Dict]:
    """解析 ``lsof -i -n -P`` 输出为结构化连接列表。

    NAME 形如：``TCP 10.0.0.1:62748->142.250.1.1:443 (ESTABLISHED)``
    或 ``TCP *:8777 (LISTEN)``。
    """
    connections: List[Dict] = []
    for line in text.splitlines():
        parts = line.split(None, 8)
        if len(parts) < 9 or parts[0] == "COMMAND":
            continue
        # NODE 列是协议（TCP/UDP），NAME 列是「地址->地址 (状态)」或「*:端口 (状态)」
        command, pid, user, _fd, _typ, _dev, _size, proto, name = parts[:9]
        state = ""
        m = _STATE_RE.search(name)
        if m:
            state = m.group(1)
        addr = _STATE_RE.sub("", name).strip()
        local = remote = ""
        if "->" in addr:
            local, remote = addr.split("->", 1)
        else:
            local = addr
        connections.append(
            {
                "command": command,
                "pid": pid,
                "user": user,
                "proto": proto,
                "local": local,
                "remote": remote,
                "state": state,
            }
        )
    return connections


def get_connections() -> Dict:
    """返回连接列表（截断到 MAX_CONNECTIONS）+ 总数 + 权限范围。"""
    res = platform_macos.lsof_connections()
    all_conns = parse_lsof(res.value)
    total = len(all_conns)
    truncated = total > config.MAX_CONNECTIONS
    return {
        "ok": True,
        "connections": all_conns[: config.MAX_CONNECTIONS],
        "total": total,
        "truncated": truncated,
        # 普通用户 lsof 只能看到自身进程；系统级连接需 sudo（P0 未实现）
        "scope": "own",
    }
