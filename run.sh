#!/usr/bin/env bash
# Script de execução rápida para o Dev Status Widget no Linux Debian

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Se existir um ambiente virtual local, ativa-o
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Executa em segundo plano se informado --bg ou -b
if [[ "$1" == "--bg" || "$1" == "-b" ]]; then
    shift
    nohup python3 "$SCRIPT_DIR/main.py" "$@" > /dev/null 2>&1 &
    echo "Dev Status Widget iniciado em segundo plano (PID: $!)."
    exit 0
fi

exec python3 "$SCRIPT_DIR/main.py" "$@"
