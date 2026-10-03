"""备份工具：把用户可写的配置文件备份到数据目录。

只接受调用方传入的常规文件路径；本工具本身不读取、不备份系统文件。
"""

from __future__ import annotations

import datetime
import os
import shutil
from typing import List

from network_console import config
from network_console.core.shell import Result


def _ensure_dir() -> None:
    os.makedirs(config.BACKUP_DIR, exist_ok=True)


def backup_file(src: str) -> Result:
    """把单个用户配置文件备份到备份目录，返回备份路径。"""
    if not src:
        return Result(ok=False, error="路径为空")
    real = os.path.realpath(src)
    if not os.path.isfile(real):
        return Result(ok=False, error="文件不存在", hint=real)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.basename(real)
    _ensure_dir()
    dest = os.path.join(config.BACKUP_DIR, "%s.%s.bak" % (base, ts))
    try:
        shutil.copy2(real, dest)
    except OSError as exc:
        return Result(ok=False, error=str(exc))
    return Result(ok=True, value=dest)


def list_backups() -> List[str]:
    """列出备份目录中的文件名。"""
    _ensure_dir()
    return sorted(os.listdir(config.BACKUP_DIR))


def clear() -> Result:
    """清空备份目录。"""
    _ensure_dir()
    try:
        for name in os.listdir(config.BACKUP_DIR):
            path = os.path.join(config.BACKUP_DIR, name)
            if os.path.isfile(path):
                os.remove(path)
    except OSError as exc:
        return Result(ok=False, error=str(exc))
    return Result(ok=True, value="已清空备份")
