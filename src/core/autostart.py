"""
Gerenciador de inicialização automática do sistema (XDG Autostart para Linux / Registro para Windows).
"""
import os
import sys
from pathlib import Path


class AutostartManager:
    AUTOSTART_FILENAME = "dev-status-widget.desktop"
    WINDOWS_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    WINDOWS_APP_NAME = "DevStatusWidget"

    @classmethod
    def get_autostart_path(cls) -> Path:
        """Retorna o caminho do arquivo .desktop em ~/.config/autostart/ (Linux)"""
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            base = Path(xdg_config_home)
        else:
            base = Path.home() / ".config"
        return base / "autostart" / cls.AUTOSTART_FILENAME

    @classmethod
    def is_enabled(cls) -> bool:
        """Verifica se o autostart está ativo (Linux ou Windows)"""
        if sys.platform == "win32":
            return cls._is_enabled_windows()
        return cls._is_enabled_linux()

    @classmethod
    def _is_enabled_linux(cls) -> bool:
        path = cls.get_autostart_path()
        if not path.exists():
            return False
        try:
            content = path.read_text(encoding="utf-8")
            if "X-GNOME-Autostart-enabled=false" in content:
                return False
            return True
        except Exception:
            return False

    @classmethod
    def _is_enabled_windows(cls) -> bool:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.WINDOWS_REG_KEY, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, cls.WINDOWS_APP_NAME)
                return True
        except Exception:
            return False

    @classmethod
    def set_enabled(cls, enable: bool, exec_path: str = None, icon_path: str = None) -> bool:
        """Ativa ou desativa a inicialização automática no sistema (Linux ou Windows)"""
        if sys.platform == "win32":
            return cls._set_enabled_windows(enable, exec_path=exec_path)
        return cls._set_enabled_linux(enable, exec_path=exec_path, icon_path=icon_path)

    @classmethod
    def _set_enabled_windows(cls, enable: bool, exec_path: str = None) -> bool:
        try:
            import winreg
            if not enable:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.WINDOWS_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.DeleteValue(key, cls.WINDOWS_APP_NAME)
                except FileNotFoundError:
                    pass
                return True

            base_dir = Path(__file__).resolve().parent.parent.parent
            if not exec_path:
                run_bat = base_dir / "run.bat"
                if run_bat.exists():
                    exec_cmd = f'"{run_bat.resolve()}" --minimized'
                else:
                    pythonw = Path(sys.executable).with_name("pythonw.exe")
                    py_exec = str(pythonw) if pythonw.exists() else sys.executable
                    exec_cmd = f'"{py_exec}" "{base_dir / "main.py"}" --minimized'
            else:
                exec_cmd = f'"{exec_path}" --minimized' if "--minimized" not in exec_path else f'"{exec_path}"'

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.WINDOWS_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, cls.WINDOWS_APP_NAME, 0, winreg.REG_SZ, exec_cmd)
            return True
        except Exception as e:
            print(f"[Autostart] Erro ao manipular registro do Windows: {e}")
            return False

    @classmethod
    def _set_enabled_linux(cls, enable: bool, exec_path: str = None, icon_path: str = None) -> bool:
        path = cls.get_autostart_path()

        if not enable:
            if path.exists():
                try:
                    path.unlink()
                except Exception as e:
                    print(f"[Autostart] Erro ao remover atalho de autostart: {e}")
                    return False
            return True

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            base_dir = Path(__file__).resolve().parent.parent.parent
            if not exec_path:
                run_sh = base_dir / "run.sh"
                if run_sh.exists():
                    exec_cmd = f"{run_sh.resolve()} --minimized"
                else:
                    exec_cmd = f"{sys.executable} {base_dir / 'main.py'} --minimized"
            else:
                exec_cmd = f"{exec_path} --minimized" if "--minimized" not in exec_path else exec_path

            if not icon_path:
                icon_path = str((base_dir / "assets" / "icon.png").resolve())

            content = f"""[Desktop Entry]
Name=Dev Status Widget
Comment=Monitor de Pull Requests e Tarefas do Jira
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Development;Utility;
StartupWMClass=dev-status-widget
X-GNOME-Autostart-enabled=true
StartupNotify=false
"""
            path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"[Autostart] Erro ao criar atalho de autostart: {e}")
            return False
