#!/usr/bin/env sh

# Run forensic discovery worker (SQLite + ArcGIS tiles + YOLO/heuristic).
# Usage: from repo root — ./scripts/run_discovery_worker.sh
# Optional: export ROOF_YOLO_WEIGHTS=/path/to/best.pt

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

if [ -f "${ROOT}/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "${ROOT}/.env"
  set +a
fi

exec python3 "${ROOT}/src/aws_discovery_worker.py"
