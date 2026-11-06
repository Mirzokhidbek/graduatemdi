#!/usr/bin/env bash
# UzTerm AI — bitta buyruq bilan ishga tushirish.
#
#   ./run.sh                 dev: backend (8000) + frontend (5173), o'zgarishlar avtomatik yangilanadi
#   ./run.sh prod            frontend build qilinadi va hammasi bitta portda: http://localhost:8000
#   ./run.sh --transformer   qo'shimcha: torch/transformers o'rnatiladi va XLM-R modeli yuklab olinadi
#
# Birinchi ishga tushirishda .venv yaratiladi va kutubxonalar o'rnatiladi.
set -euo pipefail
cd "$(dirname "$0")"

MODE=dev
TRANSFORMER=0
for arg in "$@"; do
  case "$arg" in
    prod) MODE=prod ;;
    dev) MODE=dev ;;
    --transformer) TRANSFORMER=1 ;;
    *) echo "Nomaʼlum parametr: $arg" >&2; exit 2 ;;
  esac
done

PY=${PYTHON:-python3}
if [ ! -d .venv ]; then
  echo "==> Python muhiti yaratilmoqda (.venv)"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if [ ! -f .venv/.deps-installed ] || [ requirements.txt -nt .venv/.deps-installed ]; then
  echo "==> Python kutubxonalari"
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  touch .venv/.deps-installed
fi
if [ "$TRANSFORMER" = 1 ]; then
  echo "==> torch va transformers (bir necha daqiqa)"
  pip install -q -r requirements-transformer.txt
  python scripts/download_model.py
fi

if [ ! -d frontend/node_modules ]; then
  echo "==> Frontend kutubxonalari"
  (cd frontend && npm install --silent)
fi

export PYTHONPATH=backend
if [ "$MODE" = prod ]; then
  echo "==> Frontend build"
  (cd frontend && npm run build --silent)
  echo "==> http://localhost:8000"
  UZTERM_FRONTEND_DIST=frontend/dist exec uvicorn app.main:app --host 127.0.0.1 --port 8000
fi

uvicorn app.main:app --reload --port 8000 &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null || true' EXIT INT TERM
echo "==> Backend: http://127.0.0.1:8000/docs   Frontend: http://localhost:5173"
(cd frontend && npm run dev)
