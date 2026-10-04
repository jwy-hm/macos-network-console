from __future__ import annotations

from network_console.api import dns
from network_console.core.shell import Result

# 真实 scutil --dns 输出的简化样本（含 fake-ip + mDNS + 真实 DNS）
SAMPLE = """DNS configuration

resolver #1
  nameserver[0] : 198.18.0.2
  if_index : 31 (utun13)
  flags    : Supplemental, Request A records, Request AAAA records
  reach    : 0x00000003 (Reachable,Transient Connection)
  order    : 104400

resolver #2
  domain   : local
  options  : mdns
  timeout  : 5
  flags    : Request A records, Request AAAA records
  reach    : 0x00000000 (Not Reachable)
  order    : 300000

DNS configuration (for scoped queries)

resolver #1
  nameserver[0] : 192.0.0.33
  nameserver[1] : 192.0.0.34
  if_index : 11 (en0)
  flags    : Scoped, Request A records, Request AAAA records
  reach    : 0x00000002 (Reachable)
"""


# ---------- _parse_scutil_dns ----------

def test_parse_scutil_dns_sections():
    resolvers = dns._parse_scutil_dns(SAMPLE)
    # 主段 2 个 + scoped 段 1 个
    assert len(resolvers) == 3
    assert resolvers[0]["section"] == "main"
    assert resolvers[2]["section"] == "scoped"


def test_parse_fake_ip_meaning():
    resolvers = dns._parse_scutil_dns(SAMPLE)
    # resolver #1 是 198.18.0.2（fake-ip）
    assert resolvers[0]["nameservers"] == ["198.18.0.2"]
    assert "fake-ip" in resolvers[0]["meaning"]


def test_parse_mdns_meaning():
    resolvers = dns._parse_scutil_dns(SAMPLE)
    # resolver #2 是 mDNS local 域
    assert resolvers[1]["domain"] == "local"
    assert "mDNS" in resolvers[1]["meaning"]


def test_parse_scoped_real_dns():
    resolvers = dns._parse_scutil_dns(SAMPLE)
    # scoped resolver #1 是真实 DNS 192.0.0.33/34
    assert resolvers[2]["nameservers"] == ["192.0.0.33", "192.0.0.34"]
    assert "192.0.0.33" in resolvers[2]["meaning"]


def test_parse_empty():
    assert dns._parse_scutil_dns("") == []


# ---------- _parse_service_dns ----------

def test_parse_service_dns_normal():
    assert dns._parse_service_dns("8.8.8.8\n8.8.4.4") == ["8.8.8.8", "8.8.4.4"]


def test_parse_service_dns_empty():
    assert dns._parse_service_dns("There aren't any DNS Servers set on Wi-Fi.") == []


# ---------- query_dns ----------

def test_query_dns_invalid_domain():
    result = dns.query_dns("bad; domain", "A")
    assert result["ok"] is False
    assert result["results"] == []


def test_query_dns_invalid_type():
    result = dns.query_dns("example.com", "FOO")
    assert result["ok"] is False


def test_query_dns_ok(monkeypatch):
    def fake_dig(domain, rt, timeout=None):
        return Result(ok=True, value="93.184.216.34\n")

    monkeypatch.setattr("network_console.api.dns.platform_macos.dig_query", fake_dig)
    result = dns.query_dns("example.com", "A")
    assert result["ok"] is True
    assert result["results"] == ["93.184.216.34"]
    assert result["type"] == "A"


# ---------- get_dns_overview ----------

def test_get_dns_overview(monkeypatch):
    def fake_scutil():
        return Result(ok=True, value=SAMPLE)

    def fake_services():
        return Result(ok=True, value="An asterisk (*) denotes that a network service is disabled.\nWi-Fi\nTailscale\n")

    def fake_get_dns(service):
        if service == "Wi-Fi":
            return Result(ok=True, value="There aren't any DNS Servers set on Wi-Fi.")
        return Result(ok=True, value="192.0.2.53\n")

    monkeypatch.setattr("network_console.api.dns.platform_macos.scutil_dns", fake_scutil)
    monkeypatch.setattr("network_console.api.dns.platform_macos.networksetup_list_services", fake_services)
    monkeypatch.setattr("network_console.api.dns.platform_macos.networksetup_get_dns", fake_get_dns)

    result = dns.get_dns_overview()
    assert result["ok"] is True
    assert len(result["resolvers"]) == 3
    assert len(result["services"]) == 2
    assert result["services"][0]["servers"] == []
    assert result["services"][1]["servers"] == ["192.0.2.53"]
