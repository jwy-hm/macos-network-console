from __future__ import annotations

from network_console.api import interface


def test_parse_netstat_ib_deduplicates_duplicate_rows():
    text = (
        "Name  Mtu   Network       Address            Ipkts Ierrs     Ibytes    Opkts Oerrs     Obytes  Coll\n"
        "lo0   16384 <Link#1>                        0     0          0          0     0          0      0\n"
        "en0   1500  <Link#6>       aa:bb:cc:dd:ee:ff 10    0          1000       20    0          2000    0\n"
        "en0   1500  192.168.1     192.168.1.5        5     0          500        8     0          800     0\n"
        "en0   1500  fe80::         fe80::1            1     0          10         2     0          20      0\n"
    )
    result = interface.parse_netstat_ib(text)
    names = [i["name"] for i in result]
    assert names.count("en0") == 1
    en0 = next(i for i in result if i["name"] == "en0")
    # 取三行里的最大值
    assert en0["ibytes"] == 1000
    assert en0["obytes"] == 2000
    # link 层行拿到 MAC
    assert en0["mac"] == "aa:bb:cc:dd:ee:ff"


def test_parse_ifconfig_extracts_fields():
    text = (
        "en0: flags=8863<UP,BROADCAST> mtu 1500\n"
        "\tether aa:bb:cc:dd:ee:ff\n"
        "\tinet 192.168.1.5 netmask 0xffffff00 broadcast 192.168.1.255\n"
        "\tinet6 fe80::1c8b%en0 prefixlen 64\n"
        "utun0: flags=8051<UP,POINTOPOINT> mtu 1380\n"
    )
    result = interface.parse_ifconfig(text)
    by_name = {i["name"]: i for i in result}
    en0 = by_name["en0"]
    assert en0["mtu"] == "1500"
    assert en0["mac"] == "aa:bb:cc:dd:ee:ff"
    assert en0["inet"] == "192.168.1.5"
    assert en0["inet6"] == "fe80::1c8b"
    assert en0["up"] is True
    assert "utun0" in by_name


def test_parse_default_route():
    text = "   route to: default\n    gateway: 172.20.10.1\n  interface: en0\n"
    assert interface._parse_default_route(text) == {"gateway": "172.20.10.1", "interface": "en0"}
