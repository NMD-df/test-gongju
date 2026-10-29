#!/bin/bash
# PDF 压缩工具 —— 双击启动
cd "$(dirname "$0")" || exit 1

PY=""
for c in /usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 python3; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done

if [ -z "$PY" ]; then
    echo "未找到 Python 3"
    read -r -p "按回车退出..."; exit 1
fi

# 首次运行自动补装依赖
"$PY" - <<'EOF' >/dev/null 2>&1
import importlib, subprocess, sys
need = []
for m, pkg in [("pymupdf", "pymupdf"), ("PIL", "pillow")]:
    try:
        importlib.import_module(m)
    except ImportError:
        need.append(pkg)
if need:
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet"] + need)
EOF

exec "$PY" server.py