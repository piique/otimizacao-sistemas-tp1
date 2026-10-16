#!/usr/bin/env bash
# Roda um comando Python dentro do container do projeto, sem instalar nada no host.
# Uso: ./run.sh src/meu_script.py [args...]
#      ./run.sh -m pytest
#      ./run.sh            (abre shell interativo)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${TP1_IMAGE:-otimizacao-tp1}"
USER_ARGS=(--user "$(id -u):$(id -g)")
ENV_ARGS=(-e HOME=/tmp -e MPLCONFIGDIR=/tmp/mplconfig -e XDG_CACHE_HOME=/tmp/.cache)

if [ "$#" -eq 0 ]; then
  exec docker run --rm -it "${USER_ARGS[@]}" "${ENV_ARGS[@]}" -v "$ROOT_DIR":/work -w /work "$IMAGE" bash
fi

exec docker run --rm "${USER_ARGS[@]}" "${ENV_ARGS[@]}" -v "$ROOT_DIR":/work -w /work "$IMAGE" "$@"
