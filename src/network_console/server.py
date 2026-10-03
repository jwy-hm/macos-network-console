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
from network_console.api import status as status_api

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
        elif self.path in ("/", "/index.html"):
            self._serve_index()
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
        # P0：尚无具体 POST 动作端点，先返回占位。
        self._send_json(200, {"ok": True, "value": "ok"})

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
