"""HTTP 服务层。

安全要点：
- 只监听 127.0.0.1
- HTTP/1.1 + 始终带 Content-Length
- 安全响应头（CSP / nosniff / no-referrer）
- CSRF token：POST 必须带对 token，否则 403
- 请求体大小限制
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from network_console import config
from network_console.api import connection as connection_api
from network_console.api import diagnostics as diagnostics_api
from network_console.api import interface as interface_api
from network_console.api import settings as settings_api
from network_console.api import status as status_api
from network_console.api import wifi as wifi_api

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}

# 静态资源白名单：URL 路径 -> (文件名, Content-Type)。
# 只映射已知文件、绝不拿 self.path 拼路径，避免路径穿越。
STATIC_FILES = {
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/i18n.js": ("i18n.js", "application/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "macos-network-console"
    sys_version = ""
    # CSRF token：进程启动时生成一次、全局唯一、多标签页共享。
    # 勿在每次 GET 时重新生成，否则刷新旧标签页会导致 403。
    csrf_token = ""

    def _headers(self, code: int, content_type: str, length: int) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()

    def _send_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._headers(code, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _send_text(self, code: int, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
        body = text.encode("utf-8")
        self._headers(code, content_type, len(body))
        self.wfile.write(body)

    def _serve_index(self) -> None:
        path = os.path.join(WEB_DIR, "index.html")
        try:
            with open(path, encoding="utf-8") as fh:
                html = fh.read()
        except OSError:
            self._send_json(500, {"ok": False, "error": "无法读取页面"})
            return
        html = html.replace("__CSRF_TOKEN__", self.csrf_token)
        body = html.encode("utf-8")
        self._headers(200, "text/html; charset=utf-8", len(body))
        self.wfile.write(body)

    def _serve_static(self, filename: str, content_type: str) -> None:
        path = os.path.join(WEB_DIR, filename)
        try:
            with open(path, "rb") as fh:
                body = fh.read()
        except OSError:
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        self._headers(200, content_type, len(body))
        self.wfile.write(body)

    def _read_json_body(self, length: int) -> Optional[dict]:
        """读取并解析 JSON 请求体。失败时已发送错误响应，返回 None。"""
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            self._send_json(400, {"ok": False, "error": "Content-Type 须为 application/json"})
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"ok": False, "error": "请求体不是合法 JSON"})
            return None

    def do_HEAD(self) -> None:
        if self.path == "/api/health":
            self._headers(200, "text/plain; charset=utf-8", 2)
        else:
            self._headers(405, "text/plain; charset=utf-8", 0)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_text(200, "ok")
        elif self.path == "/api/status":
            self._send_json(200, status_api.get_status())
        elif self.path == "/api/interface":
            self._send_json(200, interface_api.get_interfaces())
        elif self.path == "/api/connection":
            self._send_json(200, connection_api.get_connections())
        elif self.path == "/api/diagnostics/tools":
            self._send_json(200, diagnostics_api.get_tools())
        elif self.path == "/api/wifi":
            self._send_json(200, wifi_api.get_wifi())
        elif self.path.split("?", 1)[0] == "/api/wifi/preferred":
            self._send_json(200, wifi_api.get_preferred_networks())
        elif self.path == "/api/settings/privacy":
            self._send_json(200, settings_api.get_privacy())
        elif self.path in ("/", "/index.html"):
            self._serve_index()
        elif self.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[self.path]
            self._serve_static(filename, content_type)
        else:
            self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if self.headers.get("X-CSRF-Token") != self.csrf_token:
            self._send_json(403, {"ok": False, "error": "CSRF 校验失败"})
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > config.MAX_BODY_BYTES:
            self._send_json(413, {"ok": False, "error": "请求体过大"})
            return
        if self.path == "/api/diagnostics/run":
            body = self._read_json_body(length)
            if body is None:
                return
            result = diagnostics_api.run_tool(
                str(body.get("tool", "")), str(body.get("target", ""))
            )
            self._send_json(200, result)
            return
        if self.path == "/api/settings/privacy":
            body = self._read_json_body(length)
            if body is None:
                return
            result = settings_api.set_privacy(bool(body.get("enabled", False)))
            self._send_json(200, result)
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def log_message(self, *args) -> None:  # noqa: D401
        pass  # 默认不打日志到磁盘


def create_server(port: Optional[int]) -> HTTPServer:
    """绑定端口。

    :param port: 显式端口，占用时抛 OSError；None 时从 config.PORT 起自动 +1。
    """
    if port is not None:
        return HTTPServer(("127.0.0.1", port), Handler)

    candidate = config.PORT
    for _ in range(100):
        try:
            return HTTPServer(("127.0.0.1", candidate), Handler)
        except OSError:
            candidate += 1
    raise OSError("找不到可用端口")
