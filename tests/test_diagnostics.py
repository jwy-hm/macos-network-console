from __future__ import annotations

from network_console.api import diagnostics
from network_console.core.shell import Result


def test_parse_ping_no_loss():
    text = (
        "PING 8.8.8.8 (8.8.8.8): 56 data bytes\n"
        "64 bytes from 8.8.8.8: icmp_seq=0 ttl=116 time=10.2 ms\n"
        "--- 8.8.8.8 ping statistics ---\n"
        "5 packets transmitted, 5 packets received, 0.0% packet loss\n"
        "round-trip min/avg/max/stddev = 8.523/10.234/12.345/1.234 ms\n"
    )
    stats = diagnostics.parse_ping(text)
    assert stats["transmitted"] == 5
    assert stats["received"] == 5
    assert stats["loss"] == 0.0
    assert stats["rtt"]["avg"] == 10.234


def test_parse_ping_full_loss():
    text = (
        "PING 192.0.2.1 (192.0.2.1): 56 data bytes\n"
        "--- 192.0.2.1 ping statistics ---\n"
        "5 packets transmitted, 0 packets received, 100.0% packet loss\n"
    )
    stats = diagnostics.parse_ping(text)
    assert stats["transmitted"] == 5
    assert stats["received"] == 0
    assert stats["loss"] == 100.0
    assert stats["rtt"] == {}


def test_parse_traceroute_hops_and_timeout():
    text = (
        "traceroute to 8.8.8.8 (8.8.8.8), 20 hops max, 60 byte packets\n"
        " 1  192.168.1.1  2.123 ms\n"
        " 2  *\n"
        " 3  10.0.0.1  12.345 ms\n"
    )
    hops = diagnostics.parse_traceroute(text)
    assert [h["hop"] for h in hops] == [1, 2, 3]
    assert hops[0]["addr"] == "192.168.1.1"
    assert hops[0]["time_ms"] == [2.123]
    assert hops[1]["addr"] == ""
    assert hops[1]["time_ms"] == []


def test_parse_curl_timing_splits_headers_and_timing():
    text = (
        "HTTP/1.1 200 OK\n"
        "Content-Type: text/html\n"
        "\n"
        "---TIMING---\n"
        "namelookup:0.010\n"
        "connect:0.020\n"
        "appconnect:0.080\n"
        "starttransfer:0.120\n"
        "total:0.130\n"
    )
    parsed = diagnostics.parse_curl_timing(text)
    assert parsed["status"] == "HTTP/1.1 200 OK"
    assert parsed["redirects"] == 0
    assert parsed["timing"]["total"] == "0.130"
    assert "Content-Type" in parsed["headers"]


def test_run_tool_unknown_tool():
    result = diagnostics.run_tool("bogus", "example.com")
    assert not result["ok"]
    assert "未知工具" in result["error"]


def test_run_tool_missing_target():
    result = diagnostics.run_tool("ping", "  ")
    assert not result["ok"]
    assert result["error"] == "缺少目标"


def test_run_tool_rejects_option_injection():
    result = diagnostics.run_tool("ping", "-c 5")
    assert not result["ok"]
    assert result["error"] == "非法目标"


def test_run_http_rejects_non_http_scheme():
    result = diagnostics.run_tool("http", "file:///etc/passwd")
    assert not result["ok"]
    assert "http/https" in result["error"]


def test_probe_tools_returns_all_keys():
    tools = diagnostics.probe_tools()
    for key in ("ping", "traceroute", "curl", "dig", "nslookup", "openssl", "nc"):
        assert key in tools


def test_run_ping_uses_bsd_flags(monkeypatch):
    captured = {}

    def fake_ping(host, count=5, interval=0.2, timeout_ms=3000, timeout=None):
        captured["args"] = (host, count, interval, timeout_ms, timeout)
        return Result(ok=True, value="5 packets transmitted, 5 packets received, 0.0% packet loss\nround-trip min/avg/max/stddev = 8.5/10.2/12.3/1.2 ms\n")

    monkeypatch.setattr("network_console.api.diagnostics.platform_macos.ping_diag", fake_ping)
    result = diagnostics.run_tool("ping", "8.8.8.8")
    assert result["ok"]
    assert captured["args"] == ("8.8.8.8", 5, 0.2, 3000, 15)
    assert "0.0%" in result["summary"]


def test_is_fake_ip():
    assert diagnostics.is_fake_ip("198.18.0.5")
    assert diagnostics.is_fake_ip("198.19.255.255")
    assert diagnostics.is_fake_ip("240.1.2.3")
    assert not diagnostics.is_fake_ip("8.8.8.8")
    assert not diagnostics.is_fake_ip("192.168.1.1")
    assert not diagnostics.is_fake_ip("example.com")


def test_run_traceroute_all_hops_timeout_warning(monkeypatch):
    def fake_tr(host, max_hops=20, timeout=None):
        return Result(ok=False, value=" 1  *\n 2  *\n 3  *\n")

    monkeypatch.setattr("network_console.api.diagnostics.platform_macos.traceroute_diag", fake_tr)
    result = diagnostics.run_tool("traceroute", "8.8.8.8")
    assert result["warning"] == "all_hops_timeout"


def test_run_traceroute_no_warning_when_hops_resolve(monkeypatch):
    def fake_tr(host, max_hops=20, timeout=None):
        return Result(ok=True, value=" 1  192.168.1.1  2.1 ms\n 2  10.0.0.1  12.3 ms\n")

    monkeypatch.setattr("network_console.api.diagnostics.platform_macos.traceroute_diag", fake_tr)
    result = diagnostics.run_tool("traceroute", "8.8.8.8")
    assert "warning" not in result


def test_run_dns_fake_ip_warning(monkeypatch):
    monkeypatch.setattr("network_console.api.diagnostics.probe_tools", lambda: {"dig": True})

    def fake_dig(domain, timeout=None):
        return Result(ok=True, value="198.18.0.160\n")

    monkeypatch.setattr("network_console.api.diagnostics.platform_macos.dig_lookup", fake_dig)
    result = diagnostics.run_tool("dns", "example.com")
    assert result["warning"] == "fake_ip"


def test_get_tools_returns_timeouts():
    data = diagnostics.get_tools()
    assert data["timeouts"]["ping"] == 15
    assert data["timeouts"]["traceroute"] == 45
    assert data["timeouts"]["http"] == 15
    assert data["timeouts"]["dns"] == 10
