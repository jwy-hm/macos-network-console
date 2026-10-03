"""命令行入口。"""

from __future__ import annotations

import argparse
import secrets
import threading
import webbrowser

from network_console import server


def main() -> None:
    parser = argparse.ArgumentParser(description="macos-network-console：纯本地 macOS 网络管理控制台")
    parser.add_argument("--port", type=int, default=None, help="指定端口（被占用则直接报错退出）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    server.Handler.csrf_token = secrets.token_urlsafe(32)

    try:
        srv = server.create_server(args.port)
    except OSError as exc:
        print("启动失败：%s" % exc)
        raise SystemExit(1) from None

    port = srv.server_address[1]
    url = "http://127.0.0.1:%d" % port
    print("macos-network-console 已启动：%s" % url)
    print("按 Ctrl+C 停止。")

    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
