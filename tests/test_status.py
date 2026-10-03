from __future__ import annotations

from network_console.api import status
from network_console.core.shell import Result


def test_running_clients_matches_keywords():
    ps = "123 user /Applications/Shadowrocket.app/Contents/MacOS/MacPacketTunnel"
    assert "Shadowrocket" in status._running_clients(ps)


def test_running_clients_no_match():
    assert status._running_clients("just a normal process list") == []


def test_running_clients_filters_by_kind():
    ps = "shadowrocket macpackettunnel tailscale atrust running"
    # 只取 proxy 类：应只有 Shadowrocket，不含 Tailscale/aTrust
    assert status._running_clients(ps, kinds=["proxy"]) == ["Shadowrocket"]
    # 取 mesh/vpn/zero-trust 类：应含 Tailscale 与 aTrust
    assert set(status._running_clients(ps, kinds=["mesh", "vpn", "zero-trust"])) == {"Tailscale", "Sangfor aTrust"}


def test_check_proxy_ok_via_client():
    data = {
        "ps": Result(ok=True, value="shadowrocket macpackettunnel running"),
        "lsof": Result(ok=True, value=""),
        "proxy": Result(ok=True, value=""),
    }
    check = status.check_proxy(data)
    assert check["ok"]
    assert "Shadowrocket" in check["value"]
    assert "hint" not in check


def test_check_proxy_fallback_system_proxy():
    data = {
        "ps": Result(ok=True, value=""),
        "lsof": Result(ok=True, value=""),
        "proxy": Result(ok=True, value="HTTPEnable : 1"),
    }
    check = status.check_proxy(data)
    assert check["ok"]
    assert "系统代理" in check["value"]


def test_check_proxy_bad_has_hint():
    data = {
        "ps": Result(ok=True, value=""),
        "lsof": Result(ok=True, value=""),
        "proxy": Result(ok=True, value="HTTPEnable : 0"),
    }
    check = status.check_proxy(data)
    assert not check["ok"]
    assert "hint" in check


def test_count_10064_routes():
    text = "100.64/10  gw  UGSc en0\n100.64/10  link UCSI utun\n"
    assert status._count_10064_routes(text) == 2
    assert status._count_10064_routes("192.168.1.0/24  x\n10.0.0.0/8  y\n") == 0


def test_parse_nameservers():
    text = "resolver #1\n  nameserver[0] : 198.18.0.2\n  nameserver[1] : 8.8.8.8\n"
    assert status._parse_nameservers(text) == ["198.18.0.2", "8.8.8.8"]


def test_count_peers_stopped():
    assert status._count_peers("Tailscale is stopped.") == 0
    assert status._count_peers("") == 0
    assert status._count_peers("100.1.2.3  a  u@  macOS  -\n100.4.5.6  b  u@  iOS  offline\n") == 2
