#!/usr/bin/env python3
"""i18n 检查：除 i18n.js 外，web 下的 .js / .html 不得出现中文字符。

用 Python 而非 grep -P，避免依赖 macOS BSD grep（不支持 -P）。
CI 里与本脚本配套，每次 PR 自动挡「漏翻译」。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "src" / "network_console" / "web"
EXCLUDE = {"i18n.js"}

_PATTERN = re.compile(r"[\u4e00-\u9fff]")
failed = False

for path in sorted(WEB.rglob("*")):
    if path.name in EXCLUDE or path.suffix not in (".js", ".html"):
        continue
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if _PATTERN.search(line):
            print(f"{path.relative_to(REPO)}:{i}: {line.strip()}")
            failed = True

if failed:
    print("i18n-check 失败：发现未国际化的中文文案，请移入 web/i18n.js")
    sys.exit(1)

print("i18n-check 通过：web 前端无中文残留（i18n.js 除外）")
