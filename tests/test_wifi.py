from __future__ import annotations

import json
from pathlib import Path

import pytest

from network_console.api import wifi
from network_console.core.shell import Result

FIXTURES = Path(__file__).parent / "fixtures" / "wifi"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


HARDWARE_WIFI = (
    "Hardware Port: Wi-Fi\n"
    "Device: en0\n"
    "Ethernet Address: aa:bb:cc:dd:ee:ff\n\n"
    "Hardware Port: Thunderbolt Bridge\n"
    "Device: bridge0\n"
)


@pytest.fixture(autouse=True)
def _reset_cache():
    wifi._wifi_device = None
    yield
    wifi._wifi_device = None


# ---------- 纯解析函数 ----------

def test_parse_wifi_device_finds_en0():
    assert wifi.parse_wifi_device(HARDWARE_WIFI) == "en0"


def test_parse_wifi_device_no_wifi():
    assert wifi.parse_wifi_device(_load("no_wifi_device.txt")) == ""


def test_parse_signal_noise_merged():
    assert wifi.parse_signal_noise("-58 dBm / -97 dBm") == (-58, -97)


def test_parse_signal_noise_empty():
    assert wifi.parse_signal_noise("") == (None, None)
    assert wifi.parse_signal_noise("无信号") == (None, None)


def test_security_key_mapping():
    assert wifi.security_key("spairport_security_mode_wpa2_personal") == "wpa2_personal"
    assert wifi.security_key("spairport_security_mode_wpa3_transition") == "wpa3_transition"
    assert wifi.security_key("spairport_security_mode_none") == "open"
    assert wifi.security_key("") == ""


def test_signal_grade_thresholds():
    assert wifi.signal_grade(-45) == "excellent"
    assert wifi.signal_grade(-58) == "good"
    assert wifi.signal_grade(-65) == "fair"
    assert wifi.signal_grade(-75) == "poor"
    assert wifi.signal_grade(None) == "unknown"


def test_parse_preferred_networks_skips_title():
    nets = wifi.parse_preferred_networks(_load("preferred_networks.txt"))
    assert nets == ["TestNetwork", "OfficeNetwork", "Home-5G"]


# ---------- get_wifi ----------

def _mock(monkeypatch, hardware, system_profiler):
    monkeypatch.setattr(
        "network_console.api.wifi.platform_macos.hardware_ports",
        lambda: Result(ok=True, value=hardware),
    )
    monkeypatch.setattr(
        "network_console.api.wifi.platform_macos.wifi_info",
        lambda: Result(ok=True, value=system_profiler),
    )


def test_get_wifi_connected(monkeypatch):
    _mock(monkeypatch, HARDWARE_WIFI, _load("macos12_connected.json"))
    result = wifi.get_wifi()
    assert result["connected"] is True
    assert result["device"] == "en0"
    assert result["ssid"] == "TestNetwork"
    assert result["security"] == "wpa2_personal"
    assert result["bssid"] is None
    assert result["signal"]["rssi"] == -58
    assert result["signal"]["noise"] == -97
    assert result["signal"]["snr"] == 39
    assert result["signal"]["grade"] == "good"
    assert result["signal"]["note"] == ""


def test_get_wifi_connected_wpa3(monkeypatch):
    _mock(monkeypatch, HARDWARE_WIFI, _load("macos13_connected.json"))
    result = wifi.get_wifi()
    assert result["connected"] is True
    assert result["security"] == "wpa3_transition"
    assert result["signal"]["grade"] == "excellent"


def test_get_wifi_low_snr_note(monkeypatch):
    # rssi=-50（优）但 noise=-60 → snr=10 < 20，应标 low_snr
    low_snr = json.dumps({
        "SPAirPortDataType": [{
            "spairport_airport_interfaces": [{
                "_name": "en0",
                "spairport_status_information": "spairport_status_connected",
                "spairport_current_network_information": {
                    "_name": "CrowdedNet",
                    "spairport_security_mode": "spairport_security_mode_wpa2_personal",
                    "spairport_signal_noise": "-50 dBm / -60 dBm",
                },
            }],
        }],
    })
    _mock(monkeypatch, HARDWARE_WIFI, low_snr)
    result = wifi.get_wifi()
    assert result["signal"]["grade"] == "excellent"
    assert result["signal"]["snr"] == 10
    assert result["signal"]["note"] == "low_snr"


def test_get_wifi_disconnected(monkeypatch):
    _mock(monkeypatch, HARDWARE_WIFI, _load("disconnected.json"))
    result = wifi.get_wifi()
    assert result["connected"] is False
    assert "ssid" not in result


def test_get_wifi_no_device(monkeypatch):
    _mock(monkeypatch, _load("no_wifi_device.txt"), "{}")
    result = wifi.get_wifi()
    assert result["connected"] is False
    assert result["device"] == ""


# ---------- get_preferred_networks ----------

def test_get_preferred_networks_privacy_on():
    result = wifi.get_preferred_networks(privacy=True)
    assert result["masked"] is True
    assert result["networks"] == []
    assert result["hint"] == "privacy"


def test_get_preferred_networks_normal(monkeypatch):
    monkeypatch.setattr(
        "network_console.api.wifi.platform_macos.hardware_ports",
        lambda: Result(ok=True, value=HARDWARE_WIFI),
    )
    monkeypatch.setattr(
        "network_console.api.wifi.platform_macos.preferred_wireless_networks",
        lambda device: Result(ok=True, value=_load("preferred_networks.txt")),
    )
    result = wifi.get_preferred_networks(privacy=False)
    assert result["masked"] is False
    assert result["networks"] == ["TestNetwork", "OfficeNetwork", "Home-5G"]
