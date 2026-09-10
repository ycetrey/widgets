#!/usr/bin/env bash
# Script de execução rápida para o Dev Status Widget no Linux Debian

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Se existir um ambiente virtual local, ativa-o
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

exec python3 "$SCRIPT_DIR/main.py" "$@"
