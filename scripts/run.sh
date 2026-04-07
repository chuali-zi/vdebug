#!/usr/bin/env bash
set -euo pipefail

HOST_ADDRESS="${1:-127.0.0.1}"
PORT="${2:-8000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${REPO_ROOT}/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.venv/bin/activate"
fi

export PYTHONPATH="${REPO_ROOT}/src"

echo "Starting LOT MVP on http://${HOST_ADDRESS}:${PORT}"
echo "Repo root: ${REPO_ROOT}"

cd "${REPO_ROOT}"

python -m uvicorn lot.main:app --reload --host "${HOST_ADDRESS}" --port "${PORT}"
