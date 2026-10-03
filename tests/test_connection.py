from __future__ import annotations

from network_console.api import connection


def test_parse_lsof_established_connection():
    text = (
        "COMMAND    PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\n"
        "Shadowrocke 83643 user 12u IPv4 0x123 0t0 TCP 10.0.0.1:62748->142.250.1.1:443 (ESTABLISHED)\n"
    )
    result = connection.parse_lsof(text)
    assert len(result) == 1
    conn = result[0]
    assert conn["command"] == "Shadowrocke"
    assert conn["pid"] == "83643"
    assert conn["proto"] == "TCP"
    assert conn["local"] == "10.0.0.1:62748"
    assert conn["remote"] == "142.250.1.1:443"
    assert conn["state"] == "ESTABLISHED"


def test_parse_lsof_listening_socket():
    text = (
        "COMMAND  PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\n"
        "python3 1320 user 6u IPv6 0xabc 0t0 TCP *:8777 (LISTEN)\n"
    )
    result = connection.parse_lsof(text)
    conn = result[0]
    assert conn["proto"] == "TCP"
    assert conn["local"] == "*:8777"
    assert conn["remote"] == ""
    assert conn["state"] == "LISTEN"


def test_parse_lsof_udp_no_state():
    text = (
        "COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\n"
        "mDNSRespo 123 mdns 5u IPv4 0x1 0t0 UDP *:5353\n"
    )
    result = connection.parse_lsof(text)
    conn = result[0]
    assert conn["proto"] == "UDP"
    assert conn["state"] == ""


def test_parse_lsof_skips_header_and_short_lines():
    text = "COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\nshortline\n"
    assert connection.parse_lsof(text) == []


def test_get_connections_truncates(monkeypatch):
    from network_console.core.shell import Result

    lines = ["COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME"]
    lines += ["proc%d %d user 6u IPv4 0x0 0t0 TCP *:%d (LISTEN)" % (i, i, i) for i in range(350)]
    text = "\n".join(lines)

    monkeypatch.setattr("network_console.api.connection.platform_macos.lsof_connections",
                        lambda: Result(ok=True, value=text))
    monkeypatch.setattr("network_console.api.connection.config.MAX_CONNECTIONS", 300)
    result = connection.get_connections()
    assert result["total"] == 350
    assert result["truncated"] is True
    assert len(result["connections"]) == 300
    assert result["scope"] == "own"
