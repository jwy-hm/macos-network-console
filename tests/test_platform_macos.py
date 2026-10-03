from __future__ import annotations

from network_console.core import platform_macos
from network_console.core.shell import Result


def test_ifconfig_calls_shell_with_correct_cmd(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=10.0, sudo=False):
        captured["cmd"] = cmd
        return Result(ok=True, value="ok")

    monkeypatch.setattr("network_console.core.shell.run", fake_run)
    result = platform_macos.ifconfig()
    assert result.ok
    assert captured["cmd"] == ["ifconfig"]


def test_networksetup_get_proxy_flag(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=10.0, sudo=False):
        captured["cmd"] = cmd
        return Result(ok=True, value="ok")

    monkeypatch.setattr("network_console.core.shell.run", fake_run)
    platform_macos.networksetup_get_proxy("Wi-Fi", "http")
    assert captured["cmd"] == ["networksetup", "-getwebproxy", "Wi-Fi"]


def test_networksetup_get_proxy_unknown_kind():
    result = platform_macos.networksetup_get_proxy("Wi-Fi", "bogus")
    assert not result.ok
    assert result.error == "未知代理类型"


def test_ping_uses_bsd_flags(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=10.0, sudo=False):
        captured["cmd"] = cmd
        return Result(ok=True, value="ok")

    monkeypatch.setattr("network_console.core.shell.run", fake_run)
    platform_macos.ping("example.com", count=5, timeout_ms=3000)
    assert captured["cmd"] == ["ping", "-c", "5", "-W", "3000", "example.com"]
