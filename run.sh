#!/usr/bin/env bash
# Script de execução rápida para o Dev Status Widget no Linux Debian

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Se existir mise no ambiente do usuário, inicializa para garantir que a versão do Python configurada seja usada
if [ -x "$HOME/.local/bin/mise" ]; then
    eval "$("$HOME/.local/bin/mise" env -s bash)"
fi

# Se existir um ambiente virtual local, ativa-o
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Executa em segundo plano se informado --bg ou -b
if [[ "$1" == "--bg" || "$1" == "-b" ]]; then
    shift
    if command -v systemd-run >/dev/null 2>&1 && [ -n "$XDG_RUNTIME_DIR" ]; then
        systemctl --user reset-failed dev-status-widget >/dev/null 2>&1 || true
        systemd-run --user --unit=dev-status-widget "$SCRIPT_DIR/run.sh" "$@" > /dev/null 2>&1
        echo "Dev Status Widget iniciado em segundo plano via systemd (unidade dev-status-widget)."
        exit 0
    fi
    nohup python3 "$SCRIPT_DIR/main.py" "$@" > /dev/null 2>&1 &
    disown 2>/dev/null || true
    echo "Dev Status Widget iniciado em segundo plano (PID: $!)."
    exit 0
fi

exec python3 "$SCRIPT_DIR/main.py" "$@"
