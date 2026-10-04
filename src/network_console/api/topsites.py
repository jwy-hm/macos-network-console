"""全球热门网站测速：Tranco 榜单拉取 + 并发 ping。

数据源：
- ``https://tranco-list.eu/api/lists/date/<date>`` 查最近 7 天哪天的榜单可用
- ``https://tranco-list.eu/download/<list_id>/<limit>`` 下载榜单 CSV
- 测速走 ``curl -w '%{http_code} %{time_total}'``，并发 25

缓存：榜单拉到后进程内缓存 24h（Tranco 榜单每天更新一次，24h 内重复点不必再拉）。
这是外网请求，仅在用户主动点击「测全球 Top 100」时触发（见 docs/PRIVACY.md）。
"""

from __future__ import annotations

import datetime
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

from network_console.core import platform_macos

# 进程内缓存：{domains, fetched_at, date}
_cache: Dict[str, object] = {"domains": None, "fetched_at": None, "date": None}

# 域名白名单：小写字母数字 + 点 + 连字符，必须含点
_DOMAIN_RE = re.compile(r"^[a-z0-9.-]+$")


def clean_domain(value: str) -> Optional[str]:
    """域名清洗 + 校验，非法返回 None。"""
    d = (value or "").strip().lower()
    if _DOMAIN_RE.match(d) and "." in d:
        return d
    return None


def ping_one(domain: str) -> Dict:
    """测单个域名：curl 拿状态码 + 总耗时，返回结构化结果。"""
    d = clean_domain(domain)
    if not d:
        return {"domain": domain, "status": "-", "ms": None, "ok": False, "error": "域名不合法"}
    res = platform_macos.curl_http("https://" + d)
    # curl_http 返回 "状态码 总耗时秒"，超时/失败时 Result.ok=False
    parts = (res.value or "").split()
    status = parts[0] if parts else "000"
    ms = None
    if len(parts) > 1:
        try:
            ms = round(float(parts[1]) * 1000)
        except ValueError:
            ms = None
    ok = res.ok and status != "000"
    return {"domain": d, "status": status, "ms": ms, "ok": ok}


def ping_domains(domains: List[str]) -> List[Dict]:
    """并发测多个域名（最多 25 并发）。"""
    cleaned: List[str] = []
    seen = set()
    for d in domains:
        c = clean_domain(d)
        if c and c not in seen:
            seen.add(c)
            cleaned.append(c)
    if not cleaned:
        return []
    with ThreadPoolExecutor(max_workers=25) as ex:
        return list(ex.map(ping_one, cleaned))


def fetch_top_sites(limit: int = 100, force: bool = False) -> Tuple[Optional[List[str]], str, Optional[str]]:
    """从 Tranco 拉取全球热门网站 Top-N，返回 (domains, state, list_id)。

    state: "cache"（24h 内缓存）/ "fresh"（本次新拉）/ "no-list"（最近 7 天无可用榜单）
    """
    now = datetime.datetime.now()
    if not force and _cache["domains"] and _cache["fetched_at"]:
        age = (now - _cache["fetched_at"]).total_seconds()
        if age < 86400:  # 24h 内用缓存
            return list(_cache["domains"])[:limit], "cache", str(_cache["date"])

    list_id = None
    for back in range(0, 7):
        d = (datetime.date.today() - datetime.timedelta(days=back)).isoformat()
        res = platform_macos.curl_text(
            "https://tranco-list.eu/api/lists/date/%s" % d, max_time=15, timeout=20
        )
        if not res.ok:
            continue
        try:
            j = json.loads(res.value)
            if j.get("available"):
                list_id = j["list_id"]
                break
        except (ValueError, AttributeError):
            continue
    if not list_id:
        return None, "no-list", None

    res = platform_macos.curl_text(
        "https://tranco-list.eu/download/%s/%d" % (list_id, limit), max_time=30, timeout=40
    )
    domains: List[str] = []
    for line in (res.value or "").splitlines():
        if "," in line:
            d = clean_domain(line.split(",", 1)[1])
            if d and d not in domains:
                domains.append(d)
        if len(domains) >= limit:
            break

    _cache["domains"] = domains
    _cache["fetched_at"] = now
    _cache["date"] = list_id
    return domains, "fresh", str(list_id)


def get_topsites(limit: int = 100, force: bool = False) -> Dict:
    """GET /api/topsites：拉取榜单（带缓存），返回结构化结果。"""
    domains, state, list_id = fetch_top_sites(limit, force)
    if domains is None:
        return {"ok": False, "domains": [], "message": "拉取榜单失败，请稍后重试"}
    return {
        "ok": True,
        "domains": domains,
        "count": len(domains),
        "source": "Tranco (tranco-list.eu)",
        "cached": state == "cache",
    }


def run_ping(domains: List[str]) -> Dict:
    """POST /api/ping：并发测速，返回结构化结果。"""
    results = ping_domains(domains)
    return {"ok": True, "results": results, "count": len(results)}
