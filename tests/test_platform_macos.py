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


def test_lsof_connections_flags(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=10.0, sudo=False):
        captured["cmd"] = cmd
        return Result(ok=True, value="ok")

    monkeypatch.setattr("network_console.core.shell.run", fake_run)
    platform_macos.lsof_connections()
    assert captured["cmd"] == ["lsof", "-i", "-n", "-P"]


def test_ping_diag_bsd_flags(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=10.0, sudo=False):
        captured["cmd"] = cmd
        return Result(ok=True, value="ok")

    monkeypatch.setattr("network_console.core.shell.run", fake_run)
    platform_macos.ping_diag("8.8.8.8", count=5, interval=0.2, timeout_ms=3000)
    assert captured["cmd"] == ["ping", "-c", "5", "-i", "0.2", "-W", "3000", "8.8.8.8"]


def test_traceroute_diag_flags(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=10.0, sudo=False):
        captured["cmd"] = cmd
        return Result(ok=True, value="ok")

    monkeypatch.setattr("network_console.core.shell.run", fake_run)
    platform_macos.traceroute_diag("8.8.8.8", max_hops=20)
    assert captured["cmd"] == ["traceroute", "-n", "-w", "2", "-q", "1", "-m", "20", "8.8.8.8"]


def test_curl_timing_uses_dash_D_and_w(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=10.0, sudo=False):
        captured["cmd"] = cmd
        return Result(ok=True, value="ok")

    monkeypatch.setattr("network_console.core.shell.run", fake_run)
    platform_macos.curl_timing("https://example.com", max_time=15)
    assert captured["cmd"][0] == "curl"
    assert "-D" in captured["cmd"]
    assert "-L" in captured["cmd"]
    assert "--max-redirs" in captured["cmd"]
    assert "--max-time" in captured["cmd"]
    assert captured["cmd"][-1] == "https://example.com"
    # -w 格式串应包含时间分解标记
    assert any("namelookup" in a for a in captured["cmd"])


def test_dns_lookup_wrappers(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=10.0, sudo=False):
        captured["cmd"] = cmd
        return Result(ok=True, value="ok")

    monkeypatch.setattr("network_console.core.shell.run", fake_run)
    platform_macos.dig_lookup("example.com")
    assert captured["cmd"] == ["dig", "+short", "example.com"]
    platform_macos.nslookup_host("example.com")
    assert captured["cmd"] == ["nslookup", "example.com"]
