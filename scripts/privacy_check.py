#!/usr/bin/env python3
"""隐私自查：检测源码 / 测试 / 文档中是否残留私人标识。

与旧 privacy_check.sh 相比的三处强化（对应 2026-10-04 泄漏事件）：
1. 扫描范围覆盖 tests/ 全目录（不只 fixtures/）
2. 四段 IPv4 用 ipaddress 精确判断私网/保留段，修复旧正则漏抓四段 IP 的 bug
3. 动态读 $USER 作为本机用户名黑名单（光靠通用正则抓不住真实用户名）

检测项：
- 私网 / 保留段 IP（RFC1918 + CGNAT + fake-ip 段），跳过 CIDR 段定义
- 个人目录绝对路径 /Users/<name>
- 本机用户名（$USER）
- git 作者邮箱（非 noreply）

豁免：
- 精确白名单（见下，均为测试占位 / 回环 / 文档保留段）
- 行尾注释 ``# privacy-check: ignore``
"""

from __future__ import annotations

import ipaddress
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple

REPO = Path(__file__).resolve().parent.parent

# 扫描目录 + 根目录文档
SCAN_DIRS = ["src", "scripts", "tests", "docs"]
SCAN_ROOT_MD = ["README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md"]

# 目录名黑名单（遍历时跳过）
EXCLUDE_DIRS = {".git", "__pycache__", ".venv", ".pytest_cache", ".ruff_cache", "backups"}

# 四段 IPv4：前置不能是数字/点，后置不能是数字/点/斜杠（排除 CIDR 段定义）
_IP_RE = re.compile(r"(?<![0-9.])(?:\d{1,3}\.){3}\d{1,3}(?![0-9./])")

# 私网 / 保留段：命中这些段且不在白名单 → 报告
_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),       # RFC1918
    ipaddress.ip_network("172.16.0.0/12"),    # RFC1918
    ipaddress.ip_network("192.168.0.0/16"),   # RFC1918
    ipaddress.ip_network("100.64.0.0/10"),    # CGNAT（Tailscale 等）
    ipaddress.ip_network("198.18.0.0/15"),    # fake-ip 段（RFC 2544）
    ipaddress.ip_network("240.0.0.0/4"),      # 保留段
]

# 精确白名单：回环 / 未指定 / 测试占位 / 文档保留段 TEST-NET-1
_ALLOWED_IPS = {
    "127.0.0.1",
    "0.0.0.0",
    "10.0.0.1",          # 测试占位（lsof / traceroute fixture）
    "192.168.1.1",       # 测试占位（网关 / traceroute fixture）
    "192.168.1.5",       # 测试占位（netstat fixture）
    "192.168.1.255",     # 测试占位（广播地址）
    "172.20.10.1",       # 测试占位（default route fixture）
    "198.18.0.5",        # 测试 is_fake_ip 用例
    "198.19.255.255",    # 测试 is_fake_ip 用例（198.18/15 段边界）
    "240.1.2.3",         # 测试 is_fake_ip 用例（240/4 段）
    "198.18.0.160",      # 测试 dns fake-ip fixture
    "198.18.0.2",        # 测试 nameserver fixture
    "100.1.2.3",         # 测试 Tailscale peer fixture
    "100.4.5.6",         # 测试 Tailscale peer fixture
}

# 段白名单：RFC 5737 文档保留段（示例专用，非真实地址）
_ALLOWED_NETS = [
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
]

# 个人目录路径白名单
_ALLOWED_USERS = {"user", "example"}

# 用户名黑名单跳过集：通用英文词，会撞上代码里的标识符（如 runner 变量、test 函数），
# 不能当个人标识来查。CI 的默认用户是 runner，本地是真实用户名，两者都要能正确工作。
_SKIP_USERS = {"user", "root", "admin", "test", "runner"}

_IGNORE_MARK = "privacy-check: ignore"

_PROBLEMS: List[str] = []


def _iter_files() -> List[Path]:
    files: List[Path] = []
    self_path = Path(__file__).resolve()
    for d in SCAN_DIRS:
        base = REPO / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if p.resolve() == self_path:
                continue  # 跳过脚本自身（其白名单 IP 是检测逻辑，非泄漏）
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            files.append(p)
    for name in SCAN_ROOT_MD:
        p = REPO / name
        if p.is_file():
            files.append(p)
    return sorted(set(files))


def _check_ips(line: str, rel: str, lineno: int) -> None:
    for m in _IP_RE.finditer(line):
        token = m.group(0)
        try:
            ip = ipaddress.ip_address(token)
        except ValueError:
            continue  # 非法 IP（如 999.999.999.999），跳过
        if token in _ALLOWED_IPS or any(ip in net for net in _ALLOWED_NETS):
            continue
        if any(ip in net for net in _PRIVATE_NETS):
            _PROBLEMS.append(f"{rel}:{lineno}: 私网/保留段 IP {token}")


def _check_paths(line: str, rel: str, lineno: int) -> None:
    for m in re.finditer(r"/Users/([A-Za-z0-9_.-]+)", line):
        name = m.group(1)
        if name not in _ALLOWED_USERS:
            _PROBLEMS.append(f"{rel}:{lineno}: 个人目录 /Users/{name}")


def _check_username(line: str, rel: str, lineno: int, user: str) -> None:
    if not user or user in _SKIP_USERS or len(user) < 3:
        return
    if re.search(r"\b" + re.escape(user) + r"\b", line):
        _PROBLEMS.append(f"{rel}:{lineno}: 本机用户名 '{user}'")


def _check_git_emails() -> None:
    try:
        out = subprocess.run(
            ["git", "log", "--all", "--format=%ae"],
            capture_output=True, text=True, cwd=str(REPO),
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return
    emails = sorted({e for e in out.split() if e})
    for e in emails:
        if not e.endswith("@users.noreply.github.com"):
            _PROBLEMS.append(f"git 作者邮箱非 noreply: {e}")


def _check_history(user: str) -> None:
    """扫 git 全历史 commit message（subject + body）。

    commit message 是第三条泄漏通道——2026-10-04 就曾把真实私网 IP 写进
    commit body，文件扫描抓不到。这里用同一套检测规则扫 message 文本。
    """
    try:
        out = subprocess.run(
            ["git", "log", "--all", "--format=%H%n%s%n%b"],
            capture_output=True, text=True, cwd=str(REPO),
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return
    for line in out.splitlines():
        if _IGNORE_MARK in line:
            continue
        _check_ips(line, "git-history", 0)
        _check_paths(line, "git-history", 0)
        _check_username(line, "git-history", 0, user)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="隐私自查")
    parser.add_argument("--history", action="store_true",
                        help="额外扫描 git 全历史 commit message")
    args = parser.parse_args()

    user = os.environ.get("USER", "")
    for path in _iter_files():
        rel = str(path.relative_to(REPO))
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if _IGNORE_MARK in line:
                continue
            _check_ips(line, rel, lineno)
            _check_paths(line, rel, lineno)
            _check_username(line, rel, lineno, user)
    _check_git_emails()
    if args.history:
        _check_history(user)

    scope = f"{' '.join(SCAN_DIRS)} {' '.join(SCAN_ROOT_MD)}" + (" + git 历史" if args.history else "")
    print("== privacy-check ==")
    print(f"扫描：{scope}")
    if _PROBLEMS:
        print(f"❌ 发现 {len(_PROBLEMS)} 个问题：")
        for p in _PROBLEMS:
            print(f"  {p}")
        return 1
    print("发现 0 个问题")
    print("✅ 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
