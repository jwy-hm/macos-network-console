"""Wi-Fi 详情：当前连接信息 + 已保存网络列表。

数据源：
- ``networksetup -listallhardwareports``（快）找 Wi-Fi 主接口 device
- ``system_profiler -json SPAirPortDataType``（慢）当前连接信息
- ``networksetup -listpreferredwirelessnetworks``（快）已保存网络列表

注意：现代 macOS 的 system_profiler 不提供 BSSID（只有本机接口 MAC），
所以 BSSID 字段恒为 null，前端显示「不可用」，无需定位权限交互。
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from network_console import config
from network_console.api import settings
from network_console.core import platform_macos

# 信号噪声合并字段："-58 dBm / -97 dBm"
_SIGNAL_NOISE_RE = re.compile(r"(-?\d+)\s*dBm\s*/\s*(-?\d+)\s*dBm")

# 安全类型：原始串 -> 规范化 key（前端再映射到 i18n 文案）
_SECURITY_ALIASES = {
    "none": "open",
    "wep": "wep",
    "wpa_personal": "wpa_personal",
    "wpa_enterprise": "wpa_enterprise",
    "wpa2_personal": "wpa2_personal",
    "wpa2_enterprise": "wpa2_enterprise",
    "wpa3_personal": "wpa3_personal",
    "wpa3_enterprise": "wpa3_enterprise",
    "wpa3_transition": "wpa3_transition",
}

# Wi-Fi 主接口缓存（进程内一次；硬件不会在会话中变化）
_wifi_device: Optional[str] = None


# ---------- 纯解析函数（可单测） ----------

def parse_wifi_device(text: str) -> str:
    """从 ``networksetup -listallhardwareports`` 输出找 Wi-Fi 主接口 device（如 en0）。"""
    port = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Hardware Port:"):
            port = line.split(":", 1)[1].strip()
        elif line.startswith("Device:") and port == "Wi-Fi":
            return line.split(":", 1)[1].strip()
    return ""


def parse_signal_noise(text: str) -> Tuple[Optional[int], Optional[int]]:
    """解析合并的 RSSI/noise 字段，返回 (rssi, noise)，拿不到时返回 (None, None)。"""
    if not text:
        return None, None
    m = _SIGNAL_NOISE_RE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def security_key(mode: str) -> str:
    """原始 ``spairport_security_mode_*`` -> 规范化 key（如 wpa2_personal / open）。"""
    if not mode:
        return ""
    key = mode.replace("spairport_security_mode_", "")
    return _SECURITY_ALIASES.get(key, key)


def signal_grade(rssi: Optional[int]) -> str:
    """RSSI -> 等级 key（excellent/good/fair/poor/unknown）。阈值见 config。"""
    if rssi is None:
        return "unknown"
    for threshold, grade in config.WIFI_SIGNAL_THRESHOLDS:
        if rssi >= threshold:
            return grade
    return "poor"


def parse_preferred_networks(text: str) -> List[str]:
    """解析 ``networksetup -listpreferredwirelessnetworks`` 输出。

    第一行是标题行（"Preferred networks on en0:"），跳过。
    """
    networks: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("preferred networks"):
            continue
        networks.append(line)
    return networks


# ---------- 数据获取 ----------

def find_wifi_device() -> str:
    """找 Wi-Fi 主接口 device，进程内缓存。"""
    global _wifi_device
    if _wifi_device is None:
        res = platform_macos.hardware_ports()
        _wifi_device = parse_wifi_device(res.value) or ""
    return _wifi_device


def _find_interface(data: Dict, device: str) -> Optional[Dict]:
    """从 system_profiler JSON 里找目标接口（优先 device，回退第一个 connected）。"""
    airports = data.get("SPAirPortDataType") or []
    if not airports:
        return None
    interfaces = airports[0].get("spairport_airport_interfaces") or []
    if device:
        for ifc in interfaces:
            if ifc.get("_name") == device:
                return ifc
    for ifc in interfaces:
        if ifc.get("spairport_status_information") == "spairport_status_connected":
            return ifc
    return interfaces[0] if interfaces else None


def _parse_connected_network(iface: Dict) -> Dict:
    cinfo = iface.get("spairport_current_network_information") or {}
    rssi, noise = parse_signal_noise(cinfo.get("spairport_signal_noise", ""))
    snr = (rssi - noise) if (rssi is not None and noise is not None) else None
    grade = signal_grade(rssi)
    note = "low_snr" if (snr is not None and snr < config.WIFI_SNR_WARN) else ""
    rate = cinfo.get("spairport_network_rate")
    return {
        "ssid": cinfo.get("_name", ""),
        "bssid": None,  # 现代 macOS system_profiler 不提供 BSSID
        "security": security_key(cinfo.get("spairport_security_mode", "")),
        "channel": cinfo.get("spairport_network_channel", ""),
        "phymode": cinfo.get("spairport_network_phymode", ""),
        "rate_mbps": rate if isinstance(rate, int) else None,
        "signal": {
            "rssi": rssi,
            "noise": noise,
            "snr": snr,
            "grade": grade,
            "note": note,
        },
    }


def get_wifi() -> Dict:
    """GET /api/wifi：当前 Wi-Fi 连接信息（未连接时只返回 connected:false）。"""
    device = find_wifi_device()
    if not device:
        return {"ok": True, "connected": False, "device": ""}

    res = platform_macos.wifi_info()
    if not res.ok:
        return {"ok": True, "connected": False, "device": device, "error": res.error}

    try:
        data = json.loads(res.value)
    except ValueError:
        return {"ok": True, "connected": False, "device": device, "error": "解析失败"}

    iface = _find_interface(data, device)
    if iface is None or iface.get("spairport_status_information") != "spairport_status_connected":
        return {"ok": True, "connected": False, "device": device}

    result = {"ok": True, "connected": True, "device": device}
    result.update(_parse_connected_network(iface))
    return result


def get_preferred_networks() -> Dict:
    """GET /api/wifi/preferred：已保存网络列表。

    隐私开关来自后端进程内状态（``api.settings``），不接受客户端参数——
    隐私模式下后端直接不返回网络名（连数据都不发，而非前端遮罩）。
    """
    if settings.is_privacy_enabled():
        return {"ok": True, "masked": True, "networks": [], "hint": "privacy"}

    device = find_wifi_device()
    if not device:
        return {"ok": True, "masked": False, "networks": [], "device": ""}

    res = platform_macos.preferred_wireless_networks(device)
    networks = parse_preferred_networks(res.value)
    return {"ok": True, "masked": False, "networks": networks, "device": device}
