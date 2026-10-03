"""应用级设置状态（进程内存，不落盘）。

隐私模式是「应用级状态」，不是「每个接口的开关」。敏感接口（如
``/api/wifi/preferred``）无条件读这里的状态，不接受客户端参数，杜绝
``?privacy=0`` 这类「前端传参绕过隐私」的反模式。

进程重启后状态重置为默认（隐私关闭），不持久化、不上传。
"""

from __future__ import annotations

from typing import Dict

# 进程内存状态：隐私模式默认关闭
_privacy_enabled = False


def is_privacy_enabled() -> bool:
    """敏感接口读这个开关决定是否返回敏感数据。"""
    return _privacy_enabled


def get_privacy() -> Dict:
    """GET /api/settings/privacy：返回当前隐私状态。"""
    return {"ok": True, "enabled": _privacy_enabled}


def set_privacy(enabled: bool) -> Dict:
    """POST /api/settings/privacy：更新隐私状态（bool 强制转换）。"""
    global _privacy_enabled
    _privacy_enabled = bool(enabled)
    return {"ok": True, "enabled": _privacy_enabled}
