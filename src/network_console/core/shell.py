"""安全地执行外部命令。

安全模型：
- 只用列表参数调用 subprocess（永不 shell=True），参数不会被 shell 二次解释。
- 命令名白名单：P0 只开放只读命令；写命令已定义但未启用。
- 黑名单：即便误入白名单，万能命令（sudo/sh/bash/python/perl/open/osascript 等）也一律拒绝。
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class Result:
    """统一的结构化执行结果。"""

    ok: bool
    value: str = ""
    error: str = ""
    hint: str = ""

    def to_dict(self) -> dict:
        return {"ok": self.ok, "value": self.value, "error": self.error, "hint": self.hint}


# 永远拒绝的命令（防御纵深：即使被误加进白名单也不放行）
DENY_COMMANDS = frozenset(
    {
        "sudo", "sh", "bash", "zsh", "ksh", "dash", "csh",
        "python", "python2", "python3", "perl", "ruby", "node", "php",
        "open", "osascript", "eval", "exec", "xargs", "env",
    }
)

# P0 只读命令白名单
READ_ONLY_COMMANDS = frozenset(
    {
        "ifconfig", "netstat", "lsof", "scutil", "networksetup",
        "system_profiler", "ps", "tailscale", "dig", "nslookup",
        "openssl", "curl", "ping", "traceroute", "nc", "route",
        "sw_vers", "uname", "id", "hostname", "whoami",
    }
)

# 写命令（后续版本启用；P0 不并入白名单）
WRITE_COMMANDS = frozenset(
    {
        "networksetup", "dscacheutil", "killall", "osascript", "tailscale",
    }
)


def _command_name(cmd: List[str]) -> str:
    """取命令名（去路径前缀，防止 /usr/bin/xxx 绕过白名单）。"""
    if not cmd:
        return ""
    return cmd[0].split("/")[-1]


def is_allowed(cmd: List[str]) -> bool:
    """判断命令是否允许执行。"""
    name = _command_name(cmd)
    if not name or name in DENY_COMMANDS:
        return False
    return name in READ_ONLY_COMMANDS


def run(cmd: List[str], timeout: float = 10.0, sudo: bool = False) -> Result:
    """执行命令并返回结构化结果。

    :param cmd: 命令 + 参数列表（如 ["ping", "-c", "1", "example.com"]）
    :param timeout: 超时秒数
    :param sudo: 是否走系统授权弹窗（P0 未实现）
    """
    if sudo:
        return Result(ok=False, error="sudo 操作尚未实现", hint="后续版本通过系统授权弹窗执行")
    if not is_allowed(cmd):
        return Result(
            ok=False,
            error="命令被拒绝",
            hint="%s 不在白名单或属于被禁止的命令" % (_command_name(cmd) or "?"),
        )
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        # 超时也要保留已产生的部分输出（如 traceroute 已走完的跳）。
        # 注意：text=True 下超时时 stdout 仍是 bytes，需手动解码。
        out = getattr(exc, "stdout", None)
        if out is None:
            out = getattr(exc, "output", None)
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        return Result(ok=False, value=out or "", error="超时", hint="命令超过 %.0f 秒" % timeout)
    except FileNotFoundError:
        return Result(ok=False, error="命令不存在", hint=_command_name(cmd))
    except OSError as exc:
        return Result(ok=False, error=str(exc))

    value = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode == 0:
        return Result(ok=True, value=value)
    return Result(
        ok=False,
        value=value,
        error="exit code %d" % proc.returncode,
        hint=err or value,
    )
