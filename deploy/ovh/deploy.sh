#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p data/uploads data/audio data/generated_docs

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example (fill secrets before production use)."
fi

echo "Deploy bootstrap complete."
