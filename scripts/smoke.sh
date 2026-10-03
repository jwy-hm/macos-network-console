#!/usr/bin/env bash
# 冒烟测试：起服务 → 检查首页 + 静态资源都 200 → 关服务。
# 目的：证明「页面层」资源真的能加载（curl 只看源码，看不到 JS 是否加载成功，必须逐个验证）。
set -u
cd "$(dirname "$0")/.." || exit 1

PORT=8877
PYTHONPATH=src python3 -m network_console --no-browser --port "$PORT" &
PID=$!
trap 'kill "$PID" 2>/dev/null' EXIT

sleep 1

ok=1
for f in / /app.js /style.css /i18n.js; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT$f")
  echo "$code $f"
  [ "$code" = "200" ] || ok=0
done

if [ "$ok" = "1" ]; then
  echo "smoke 通过：首页 + 静态资源全 200"
else
  echo "smoke 失败：存在非 200 资源"
  exit 1
fi
