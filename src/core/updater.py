"""
Módulo de detecção e aplicação de atualizações do Git para o Dev Status Widget.
Verifica novas alterações no repositório remoto (origin), faz git pull e reinicia a aplicação.
"""
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class UpdateInfo:
    available: bool = False
    current_commit: str = ""
    remote_commit: str = ""
    branch: str = "main"
    commits_behind: int = 0
    changelog: List[str] = field(default_factory=list)
    error: Optional[str] = None
    checked_at: Optional[datetime] = None

    @property
    def summary(self) -> str:
        if not self.available:
            return "O aplicativo já está na versão mais recente."
        commit_text = "commit novo" if self.commits_behind == 1 else "commits novos"
        return f"Nova atualização disponível ({self.commits_behind} {commit_text})."


class GitUpdater:
    def __init__(self, repo_dir: Optional[Path] = None):
        if repo_dir:
            self.repo_dir = Path(repo_dir).resolve()
        else:
            self.repo_dir = Path(__file__).resolve().parent.parent.parent

    def _run_git(self, args: List[str], timeout: int = 15) -> Tuple[int, str, str]:
        """Executa um comando git no diretório do repositório."""
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=str(self.repo_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return -1, "", str(e)

    def get_current_branch(self) -> str:
        code, out, _ = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        return out if code == 0 and out else "main"

    def get_current_commit(self, short: bool = True) -> str:
        args = ["rev-parse", "--short", "HEAD"] if short else ["rev-parse", "HEAD"]
        code, out, _ = self._run_git(args)
        return out if code == 0 else ""

    def has_local_changes(self, include_untracked: bool = False) -> bool:
        """Verifica se existem alterações locais não salvas/commitadas."""
        code, out, _ = self._run_git(["status", "--porcelain"])
        if code != 0 or not out:
            return False
        lines = out.splitlines()
        if not include_untracked:
            # Considera apenas arquivos modificados/rastreados (ignora ??)
            lines = [line for line in lines if not line.startswith("??")]
        return len(lines) > 0

    def check_for_updates(self, remote_name: str = "origin") -> UpdateInfo:
        """
        Verifica se existem novos commits no repositório remoto.
        Executa 'git fetch' de forma segura com timeout para não travar a aplicação.
        """
        now = datetime.now(timezone.utc)
        branch = self.get_current_branch()
        current_commit = self.get_current_commit(short=False)

        # 1. Fetch do branch remoto
        code, _, err = self._run_git(["fetch", remote_name, branch], timeout=20)
        if code != 0:
            return UpdateInfo(
                available=False,
                current_commit=current_commit[:7] if current_commit else "",
                branch=branch,
                error=f"Falha ao conectar ao repositório remoto: {err}",
                checked_at=now
            )

        # 2. Obter hash do commit remoto
        remote_ref = f"{remote_name}/{branch}"
        code, remote_commit, err = self._run_git(["rev-parse", remote_ref])
        if code != 0 or not remote_commit:
            return UpdateInfo(
                available=False,
                current_commit=current_commit[:7] if current_commit else "",
                branch=branch,
                error=f"Não foi possível obter a referência remota {remote_ref}: {err}",
                checked_at=now
            )

        # 3. Compara os commits
        if current_commit == remote_commit:
            return UpdateInfo(
                available=False,
                current_commit=current_commit[:7],
                remote_commit=remote_commit[:7],
                branch=branch,
                commits_behind=0,
                checked_at=now
            )

        # 4. Verifica se estamos atrás do remoto
        code, count_str, _ = self._run_git(["rev-list", f"HEAD..{remote_ref}", "--count"])
        commits_behind = int(count_str) if code == 0 and count_str.isdigit() else 0

        if commits_behind > 0:
            # Coleta as mensagens dos commits novos para o changelog
            code, log_str, _ = self._run_git([
                "log",
                f"HEAD..{remote_ref}",
                "--pretty=format:%s (%h)",
                "-n", "10"
            ])
            changelog = [msg.strip() for msg in log_str.splitlines() if msg.strip()] if code == 0 else []

            return UpdateInfo(
                available=True,
                current_commit=current_commit[:7],
                remote_commit=remote_commit[:7],
                branch=branch,
                commits_behind=commits_behind,
                changelog=changelog,
                checked_at=now
            )

        return UpdateInfo(
            available=False,
            current_commit=current_commit[:7],
            remote_commit=remote_commit[:7],
            branch=branch,
            commits_behind=0,
            checked_at=now
        )

    def apply_update(self, remote_name: str = "origin") -> Tuple[bool, str]:
        """
        Aplica a atualização executando 'git pull'.
        Retorna (sucesso, mensagem).
        """
        if self.has_local_changes():
            return False, "Existem arquivos modificados localmente. Por favor, descarte ou faça commit das suas alterações antes de atualizar."

        branch = self.get_current_branch()
        code, out, err = self._run_git(["pull", "--ff-only", remote_name, branch], timeout=30)
        if code != 0:
            # Tenta fallback para git pull padrão
            code, out, err = self._run_git(["pull", remote_name, branch], timeout=30)
            if code != 0:
                error_detail = err or out or "Erro desconhecido ao executar git pull"
                return False, f"Erro no git pull: {error_detail}"

        return True, "Repositório atualizado com sucesso!"

    def restart_application(self, extra_args: Optional[List[str]] = None):
        """
        Reinicia a aplicação de forma limpa e desacoplada, liberando os recursos da instância atual.
        """
        args = extra_args if extra_args is not None else sys.argv[1:]

        if sys.platform == "win32":
            run_bat = self.repo_dir / "run.bat"
            if run_bat.exists():
                cmd = [str(run_bat)] + args
            else:
                main_py = self.repo_dir / "main.py"
                pythonw = Path(sys.executable).with_name("pythonw.exe")
                py_exec = str(pythonw) if pythonw.exists() else sys.executable
                cmd = [py_exec, str(main_py)] + args
        else:
            run_sh = self.repo_dir / "run.sh"
            if run_sh.exists() and os.access(run_sh, os.X_OK):
                cmd = [str(run_sh)] + args
            else:
                main_py = self.repo_dir / "main.py"
                cmd = [sys.executable, str(main_py)] + args

        # Tenta encerrar o QApplication de forma limpa se estiver rodando
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.quit()
        except Exception:
            pass

        # Inicia novo processo em sessão/processo separado para não ser encerrado junto
        popen_kwargs = {"cwd": str(self.repo_dir)}
        if sys.platform == "win32":
            creation_flags = 0
            if hasattr(subprocess, "DETACHED_PROCESS"):
                creation_flags |= subprocess.DETACHED_PROCESS
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                creation_flags |= subprocess.CREATE_NEW_PROCESS_GROUP
            if creation_flags:
                popen_kwargs["creationflags"] = creation_flags
        else:
            popen_kwargs["start_new_session"] = True

        subprocess.Popen(cmd, **popen_kwargs)
        sys.exit(0)
