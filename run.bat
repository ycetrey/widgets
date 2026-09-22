@echo off
setlocal
cd /d "%~dp0"

:: Define se usa pythonw (silencioso, sem janela de console) ou python (com terminal para depuração)
set "PYTHON_EXE=pythonw.exe"
for %%a in (%*) do (
    if "%%a"=="--debug" set "PYTHON_EXE=python.exe"
    if "%%a"=="-d" set "PYTHON_EXE=python.exe"
    if "%%a"=="--demo" set "PYTHON_EXE=python.exe"
)

:: Verifica se existe ambiente virtual local (venv)
if exist "%~dp0venv\Scripts\python.exe" (
    if "%PYTHON_EXE%"=="pythonw.exe" (
        if exist "%~dp0venv\Scripts\pythonw.exe" (
            set "PY_CMD=%~dp0venv\Scripts\pythonw.exe"
        ) else (
            set "PY_CMD=%~dp0venv\Scripts\python.exe"
        )
    ) else (
        set "PY_CMD=%~dp0venv\Scripts\python.exe"
    )
) else (
    set "PY_CMD=%PYTHON_EXE%"
)

:: Inicia o aplicativo
if "%PYTHON_EXE%"=="pythonw.exe" (
    start "" "%PY_CMD%" "%~dp0main.py" %*
) else (
    "%PY_CMD%" "%~dp0main.py" %*
)
endlocal
