@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo   Instalacao do Dev Status Widget para Windows
echo ==========================================================
echo.

:: 1. Verifica se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no sistema ou nao esta no PATH.
    echo Por favor, instale o Python 3.10+ pelo site oficial (https://www.python.org/)
    echo e lembre-se de marcar a opcao "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)

:: 2. Cria ambiente virtual venv se nao existir
echo [1/3] Configurando ambiente virtual Python (venv)...
if not exist "%~dp0venv" (
    python -m venv "%~dp0venv"
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual venv.
        pause
        exit /b 1
    )
    echo Ambiente virtual criado com sucesso em "%~dp0venv".
) else (
    echo Ambiente virtual existente detectado.
)

:: 3. Instala dependencias via pip
echo.
echo [2/3] Instalando dependencias do projeto via pip...
"%~dp0venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"%~dp0venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo [AVISO] Ocorreu uma falha na instalacao de algumas dependencias.
    echo Tentando instalar componentes principais (PyQt6, requests, PyYAML)...
    "%~dp0venv\Scripts\python.exe" -m pip install PyQt6 requests PyYAML
)

:: 4. Cria atalho na Area de Trabalho (Desktop)
echo.
echo [3/3] Criando atalho na Area de Trabalho...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Dev Status Widget.lnk')); $s.TargetPath = '%~dp0run.bat'; $s.IconLocation = '%~dp0assets\icon.ico'; $s.WorkingDirectory = '%~dp0'; $s.Save()" >nul 2>&1
if %errorlevel% equ 0 (
    echo Atalho 'Dev Status Widget' criado com sucesso na sua Area de Trabalho!
) else (
    echo Nao foi possivel criar o atalho automaticamente. Voce pode executar via run.bat.
)

echo.
echo ==========================================================
echo   Instalacao concluida com sucesso!
echo ==========================================================
echo Para iniciar o widget:
echo   - Execute: run.bat
echo   - Ou de um duplo clique no atalho criado na Area de Trabalho.
echo.
pause
endlocal
