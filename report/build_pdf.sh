#!/usr/bin/env bash
# Gera report/relatorio.pdf a partir de report/relatorio.md usando pandoc+xelatex
# em um container (nada e instalado no host).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="tp1-pdf"

docker build -q -t "$IMAGE" "$ROOT/report" -f "$ROOT/report/Dockerfile.pdf" >/dev/null

docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$ROOT":/data -w /data/report "$IMAGE" \
  --pdf-engine=xelatex \
  --lua-filter=pdf_filter.lua \
  -V mainfont="DejaVu Sans" \
  -V monofont="DejaVu Sans Mono" \
  -V geometry:margin=2.5cm \
  -V colorlinks=true \
  -V linkcolor=blue \
  -o relatorio.pdf relatorio.md

echo "Gerado: report/relatorio.pdf"
