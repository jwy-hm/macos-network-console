#!/usr/bin/env bash
# 隐私自查：检查源码里是否残留私人标识。
# 使用中性正则，不写死任何具体人名 / 域名 / 路径。
# 跳过二进制文件与缓存目录（.pyc 字节码会内嵌源文件路径，属误报）。
set -u
cd "$(dirname "$0")/.." || exit 1
fail=0

GREP=(grep -rnI --exclude-dir=__pycache__ --exclude-dir=.venv --exclude-dir=.git)

echo "== 隐私自查（中性正则）=="

# 1. 私网 IP（RFC1918 + 链路本地），排除回环/广播/0.0.0.0
echo "-- 私网 IP 检查 --"
hits=$("${GREP[@]}" -E '(^|[^0-9.])(10|172\.(1[6-9]|2[0-9]|3[01])|192\.168)\.([0-9]{1,3}\.)[0-9]{1,3}([^0-9.]|$)' \
  src/ scripts/ 2>/dev/null)
if [ -n "$hits" ]; then
  echo "$hits"
  fail=1
fi

# 2. 个人目录绝对路径
echo "-- 个人目录路径检查 --"
hits=$("${GREP[@]}" -E '/Users/[A-Za-z0-9_.-]+|/home/[A-Za-z0-9_.-]+' src/ scripts/ 2>/dev/null)
if [ -n "$hits" ]; then
  echo "$hits"
  fail=1
fi

# 3. git 作者身份（供人工确认是否愿意随 commit 历史公开，仅展示、不判定）
echo "-- git 作者邮箱检查（人工确认）--"
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
  git log --all --format='%an <%ae>' 2>/dev/null | sort -u
  echo "（以上作者身份会随 commit 历史公开，请确认是否愿意公开）"
else
  echo "（非 git 仓库，跳过）"
fi

if [ "$fail" -eq 0 ]; then
  echo "通过：未发现私网 IP / 个人目录路径。"
else
  echo "发现疑似私人标识，见上方输出。"
fi
exit "$fail"
