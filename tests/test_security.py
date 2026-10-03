"""P0-16 安全对抗测试：起真实服务，用 raw socket 发请求，验证服务端防御。

不依赖任何 HTTP 客户端（客户端会先把路径 normalize 掉），直接构造原始请求字节，
确保路径穿越 / Content-Type / 超大 body / CSRF 的校验确实在服务端触发。
"""

from __future__ import annotations

import socket
import threading

import pytest

from network_console import config
from network_console.server import Handler, create_server

TOKEN = "test-csrf-token"


@pytest.fixture(scope="module")
def running_server():
    Handler.csrf_token = TOKEN
    srv = create_server(0)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield ("127.0.0.1", port)
    srv.shutdown()
    srv.server_close()


def _send_raw(addr, request: bytes) -> bytes:
    host, port = addr
    sock = socket.create_connection((host, port), timeout=5)
    sock.sendall(request)
    data = b""
    sock.settimeout(5)
    try:
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                break
            data += chunk
    except (socket.timeout, OSError):
        pass
    sock.close()
    return data


def _status(data: bytes) -> int:
    line = data.split(b"\r\n", 1)[0].decode("utf-8", "replace")
    parts = line.split(" ")
    return int(parts[1]) if len(parts) > 1 else 0


def test_post_wrong_csrf_token_returns_403(running_server):
    req = (
        b"POST /api/diagnostics/run HTTP/1.1\r\n"
        b"Host: x\r\n"
        b"X-CSRF-Token: wrong-token\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 2\r\n"
        b"Connection: close\r\n\r\n"
        b"{}"
    )
    assert _status(_send_raw(running_server, req)) == 403


def test_post_oversized_body_returns_413(running_server):
    # Content-Length 超过上限，服务端应在读 body 之前就拒绝
    too_big = config.MAX_BODY_BYTES + 1
    req = (
        b"POST /api/diagnostics/run HTTP/1.1\r\n"
        b"Host: x\r\n"
        b"X-CSRF-Token: " + TOKEN.encode() + b"\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(too_big).encode() + b"\r\n"
        b"Connection: close\r\n\r\n"
    )
    assert _status(_send_raw(running_server, req)) == 413


def test_post_wrong_content_type_returns_400(running_server):
    body = b'{"tool":"ping","target":"8.8.8.8"}'
    req = (
        b"POST /api/diagnostics/run HTTP/1.1\r\n"
        b"Host: x\r\n"
        b"X-CSRF-Token: " + TOKEN.encode() + b"\r\n"
        b"Content-Type: text/plain\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
        b"Connection: close\r\n\r\n" + body
    )
    assert _status(_send_raw(running_server, req)) == 400


def test_path_traversal_raw_returns_404(running_server):
    resp = _send_raw(
        running_server,
        b"GET /../../etc/passwd HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n",
    )
    assert _status(resp) == 404
    assert b"root:" not in resp  # 不得返回 /etc/passwd 内容


def test_path_traversal_encoded_returns_404(running_server):
    resp = _send_raw(
        running_server,
        b"GET /%2e%2e/%2e%2e/etc/passwd HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n",
    )
    assert _status(resp) == 404
    assert b"root:" not in resp


def test_api_dotdot_returns_404(running_server):
    resp = _send_raw(
        running_server,
        b"GET /api/../server.py HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n",
    )
    assert _status(resp) == 404
    assert b"class Handler" not in resp  # 不得返回 server.py 源码


def test_static_files_served(running_server):
    for path in ("/app.js", "/style.css", "/i18n.js"):
        resp = _send_raw(
            running_server,
            ("GET " + path + " HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n").encode(),
        )
        assert _status(resp) == 200, path
