#!/usr/bin/env bash
# 启动 macos-network-console。
# 用 $(cd ... && pwd) 取路径，兼容中文与空格路径；不硬编码任何个人目录。

set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1

# 解析 --port（显式端口：占用即报错退出）
PORT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --port)
      PORT="$2"
      shift 2
      ;;
    --no-browser)
      NO_BROWSER=1
      shift
      ;;
    *)
      shift
      ;;
  esac
done

# 探测 python3（要求 ≥ 3.9）
if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3，请先安装（macOS 通常自带，或通过 Homebrew 安装）。"
  exit 1
fi

MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])' 2>/dev/null)
MINOR=$(python3 -c 'import sys; print(sys.version_info[1])' 2>/dev/null)
if [ -z "$MAJOR" ] || [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 9 ]; }; then
  echo "需要 python3 ≥ 3.9，当前为 $(python3 --version 2>&1)。"
  echo "请升级：brew install python@3.11 或从 python.org 下载安装。"
  exit 1
fi

export PYTHONPATH="$DIR/src${PYTHONPATH:+:$PYTHONPATH}"

ARGS=()
[ -n "${PORT:-}" ] && ARGS+=("--port" "$PORT")
[ -n "${NO_BROWSER:-}" ] && ARGS+=("--no-browser")

exec python3 -m network_console "${ARGS[@]}"
