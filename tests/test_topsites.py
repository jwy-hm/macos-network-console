from __future__ import annotations

import json

from network_console.api import topsites
from network_console.core.shell import Result

# ---------- clean_domain ----------

def test_clean_domain_valid():
    assert topsites.clean_domain("  Example.COM  ") == "example.com"
    assert topsites.clean_domain("sub.domain-1.org") == "sub.domain-1.org"


def test_clean_domain_invalid():
    assert topsites.clean_domain("not-a-domain") is None
    assert topsites.clean_domain("has space.com") is None
    assert topsites.clean_domain("https://example.com") is None
    assert topsites.clean_domain("") is None
    assert topsites.clean_domain("例子.com") is None


# ---------- ping_domains ----------

def test_ping_domains_cleans_and_dedupes(monkeypatch):
    def fake_curl_http(url):
        # 返回 "200 0.123"（状态码 + 秒）
        return Result(ok=True, value="200 0.123")

    monkeypatch.setattr("network_console.api.topsites.platform_macos.curl_http", fake_curl_http)
    results = topsites.ping_domains(["Example.COM", "example.com", "invalid name", "no-dot"])
    # 去重后只剩 example.com 一个合法域名
    assert len(results) == 1
    assert results[0]["domain"] == "example.com"
    assert results[0]["ok"] is True
    assert results[0]["status"] == "200"
    assert results[0]["ms"] == 123


def test_ping_one_timeout(monkeypatch):
    def fake_curl_http(url):
        return Result(ok=False, value="", error="超时")

    monkeypatch.setattr("network_console.api.topsites.platform_macos.curl_http", fake_curl_http)
    results = topsites.ping_domains(["example.com"])
    assert results[0]["ok"] is False
    assert results[0]["status"] == "000"


def test_ping_domains_empty():
    assert topsites.ping_domains([]) == []
    assert topsites.ping_domains(["invalid", "no-dot"]) == []


# ---------- fetch_top_sites ----------

def _mock_curl(monkeypatch, responses):
    """按 URL 返回预设响应。"""
    calls = {}

    def fake_curl_text(url, **kwargs):
        calls[url] = calls.get(url, 0) + 1
        return responses.get(url, Result(ok=False, value="", error="fail"))

    monkeypatch.setattr("network_console.api.topsites.platform_macos.curl_text", fake_curl_text)
    return calls


def test_fetch_top_sites_fresh(monkeypatch):
    monkeypatch.setattr("network_console.api.topsites._cache",
                        {"domains": None, "fetched_at": None, "date": None})
    responses = {
        "https://tranco-list.eu/api/lists/date/2026-10-04": Result(
            ok=True, value=json.dumps({"available": True, "list_id": "abc123"})),
        "https://tranco-list.eu/download/abc123/100": Result(
            ok=True, value="1,Example.com\n2,Test.org\n3,Another.net\n"),
    }
    _mock_curl(monkeypatch, responses)
    domains, state, list_id = topsites.fetch_top_sites(100)
    assert domains == ["example.com", "test.org", "another.net"]
    assert state == "fresh"
    assert list_id == "abc123"


def test_fetch_top_sites_cache(monkeypatch):
    import datetime
    monkeypatch.setattr("network_console.api.topsites._cache", {
        "domains": ["cached.com"],
        "fetched_at": datetime.datetime.now(),
        "date": "xyz789",
    })
    # 不应再发 curl 请求
    calls = _mock_curl(monkeypatch, {})
    domains, state, list_id = topsites.fetch_top_sites(100)
    assert domains == ["cached.com"]
    assert state == "cache"
    assert list_id == "xyz789"
    assert calls == {}


def test_fetch_top_sites_no_list(monkeypatch):
    monkeypatch.setattr("network_console.api.topsites._cache",
                        {"domains": None, "fetched_at": None, "date": None})
    # 7 天都不 available
    _mock_curl(monkeypatch, {
        url: Result(ok=True, value=json.dumps({"available": False}))
        for url in ["https://tranco-list.eu/api/lists/date/2026-10-0%d" % d for d in range(4, 10)]
    })
    domains, state, list_id = topsites.fetch_top_sites(100)
    assert domains is None
    assert state == "no-list"


# ---------- get_topsites / run_ping ----------

def test_get_topsites_ok(monkeypatch):
    monkeypatch.setattr("network_console.api.topsites.fetch_top_sites",
                        lambda limit, force: (["a.com", "b.com"], "fresh", "id1"))
    result = topsites.get_topsites(100)
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["cached"] is False


def test_get_topsites_failure(monkeypatch):
    monkeypatch.setattr("network_console.api.topsites.fetch_top_sites",
                        lambda limit, force: (None, "no-list", None))
    result = topsites.get_topsites(100)
    assert result["ok"] is False
    assert result["domains"] == []


def test_run_ping(monkeypatch):
    monkeypatch.setattr("network_console.api.topsites.ping_domains",
                        lambda domains: [{"domain": d, "ok": True} for d in domains])
    result = topsites.run_ping(["a.com", "b.com"])
    assert result["ok"] is True
    assert result["count"] == 2
