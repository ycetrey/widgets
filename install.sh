#!/usr/bin/env bash
# ==============================================================================
# Script de Instalação do Dev Status Widget no Debian / Ubuntu (GNOME)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_ENTRY_DIR="$HOME/.local/share/applications"
ICON_PATH="$SCRIPT_DIR/assets/icon.png"
EXEC_PATH="$SCRIPT_DIR/run.sh"

SKIP_PERMISSIONS=false
for arg in "$@"; do
    case $arg in
        --dangerous-skip-permissions|--dangerously-skip-permissions|-y)
            SKIP_PERMISSIONS=true
            export DEBIAN_FRONTEND=noninteractive
            echo "[Aviso] Modo --dangerous-skip-permissions ativado: instalando sem confirmações interativas."
            ;;
    esac
done

echo "=========================================================="
echo "  Instalação do Dev Status Widget para Linux Debian/GNOME "
echo "=========================================================="

# 1. Verifica privilégios e instala dependências do sistema
echo ""
echo "[1/4] Instalando dependências de sistema via APT..."
if command -v apt-get &> /dev/null; then
    echo "Identificado Debian/Ubuntu. Instalando pacotes essenciais..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        python3 \
        python3-pip \
        python3-pyqt6 \
        python3-pyqt6.qtsvg \
        python3-requests \
        python3-yaml \
        libnotify-bin \
        gnome-shell-extension-appindicator || {
            echo "Aviso: alguns pacotes do sistema falharam. Tentaremos instalar via pip..."
        }
else
    echo "Gerenciador apt-get não encontrado. Pulando etapa de pacotes do sistema."
fi

# 2. Configura dependências Python
echo ""
echo "[2/4] Verificando dependências Python..."
if ! python3 -c "import PyQt6, requests, yaml" &> /dev/null; then
    echo "Instalando dependências via pip para o usuário atual..."
    pip3 install --user -r "$SCRIPT_DIR/requirements.txt" || {
        echo "Aviso: 'pip3 install' falhou ou ambiente requer venv. Criando venv local..."
        python3 -m venv "$SCRIPT_DIR/venv"
        source "$SCRIPT_DIR/venv/bin/activate"
        pip install -r "$SCRIPT_DIR/requirements.txt"
    }
else
    echo "Todas as bibliotecas Python (PyQt6, requests, pyyaml) já estão disponíveis!"
fi

# 3. Permissões de execução
echo ""
echo "[3/4] Configurando permissões de execução dos scripts..."
chmod +x "$SCRIPT_DIR/main.py"
chmod +x "$SCRIPT_DIR/run.sh"

# 4. Criando Atalho de Aplicativo no GNOME (.desktop)
echo ""
echo "[4/5] Criando atalho no menu de aplicativos do GNOME..."
mkdir -p "$DESKTOP_ENTRY_DIR"

DESKTOP_FILE="$DESKTOP_ENTRY_DIR/dev-status-widget.desktop"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=Dev Status Widget
Comment=Monitor de Pull Requests e Métricas com Abas e Notificações
Exec=$EXEC_PATH
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Development;Utility;
StartupNotify=true
StartupWMClass=dev-status-widget
EOF

chmod +x "$DESKTOP_FILE"

# Atualiza base de dados do desktop
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_ENTRY_DIR" &> /dev/null || true
fi

# 5. Configurando Inicialização Automática com o Sistema (Autostart)
echo ""
echo "[5/5] Configurando inicialização automática no login (Autostart)..."
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
AUTOSTART_FILE="$AUTOSTART_DIR/dev-status-widget.desktop"

cat <<EOF > "$AUTOSTART_FILE"
[Desktop Entry]
Name=Dev Status Widget
Comment=Monitor de Pull Requests e Métricas com Abas e Notificações
Exec=$EXEC_PATH --minimized
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Development;Utility;
StartupWMClass=dev-status-widget
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF

chmod +x "$AUTOSTART_FILE"
echo "Atalho de inicialização criado em: $AUTOSTART_FILE"

echo ""
echo "=========================================================="
echo "  Instalação concluída com sucesso!"
echo "=========================================================="
echo ""
echo "Para iniciar o widget agora, execute:"
echo "  $EXEC_PATH"
echo ""
echo "Ou pesquise por 'Dev Status Widget' no menu de aplicativos do GNOME."
echo ""
echo "Dica para GNOME:"
echo "Para que o ícone na bandeja superior apareça no GNOME Shell,"
echo "certifique-se de que a extensão 'AppIndicator and KStatusNotifierItem Support'"
echo "esteja ativada no aplicativo 'Extensões' (gnome-extensions-app)."
echo "=========================================================="
