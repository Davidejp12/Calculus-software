#!/bin/zsh
# Doppio clic per aprire "Analisi · verifica" nel browser (http://localhost:8810)
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Prima installazione…"
  python3 -m venv .venv && .venv/bin/pip install -q sympy
fi
if lsof -i :8810 -sTCP:LISTEN >/dev/null 2>&1; then
  open http://localhost:8810
else
  .venv/bin/python server.py
fi
