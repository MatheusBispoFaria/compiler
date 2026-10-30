#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

python -m pip install -r requirements.txt
npm --prefix frontend ci --include=dev --no-audit --no-fund
npm --prefix frontend run build
python -m unittest discover -s tests -v
