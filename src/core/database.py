"""
Camada de persistência local SQLite para o Dev Status Widget.
Salva tarefas do Jira, Pull Requests e histórico de notificações.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set

from .models import JiraTaskItem, NotificationItem, PullRequestItem


class DatabaseManager:
    APP_DIR_NAME = "dev-status-widget"
    DB_FILENAME = "widget.db"

    def __init__(self, custom_path: Optional[str] = None):
        self._db_path = self._resolve_db_path(custom_path)
        self._init_db()

    def _resolve_db_path(self, custom_path: Optional[str] = None) -> Path:
        if custom_path:
            p = Path(custom_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            return p

        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base_dir = Path(xdg_data) / self.APP_DIR_NAME
        else:
            base_dir = Path.home() / ".local" / "share" / self.APP_DIR_NAME

        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / self.DB_FILENAME

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jira_tasks (
                    key TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    assignee TEXT NOT NULL,
                    assignee_avatar TEXT,
                    parent_key TEXT,
                    parent_summary TEXT,
                    parent_status TEXT,
                    parent_issue_type TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    html_url TEXT NOT NULL,
                    last_synced_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS pull_requests (
                    id INTEGER PRIMARY KEY,
                    number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    repo TEXT NOT NULL,
                    author TEXT NOT NULL,
                    author_avatar TEXT,
                    html_url TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    is_draft INTEGER DEFAULT 0,
                    labels TEXT,
                    comments_count INTEGER DEFAULT 0,
                    review_decision TEXT,
                    last_synced_at TEXT NOT NULL
                )
            """)

            # Migração idempotente para bancos existentes
            try:
                conn.execute("ALTER TABLE pull_requests ADD COLUMN review_decision TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE pull_requests ADD COLUMN checks_summary TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE pull_requests ADD COLUMN checks_state TEXT")
            except sqlite3.OperationalError:
                pass

            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications_seen (
                    item_key TEXT PRIMARY KEY,
                    item_type TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_key TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    link_url TEXT,
                    created_at TEXT NOT NULL,
                    is_dismissed INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_dismissed_created
                ON notifications (is_dismissed, created_at DESC)
            """)
            conn.commit()

    def _parse_iso(self, iso_str: Optional[str]) -> Optional[datetime]:
        if not iso_str:
            return None
        try:
            return datetime.fromisoformat(iso_str)
        except Exception:
            return datetime.now(timezone.utc)

    def save_jira_tasks(self, tasks: List[JiraTaskItem]):
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM jira_tasks")
            for t in tasks:
                conn.execute("""
                    INSERT OR REPLACE INTO jira_tasks (
                        key, summary, status, status_category, priority, issue_type,
                        assignee, assignee_avatar, parent_key, parent_summary,
                        parent_status, parent_issue_type, created_at, updated_at,
                        html_url, last_synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    t.key,
                    t.summary,
                    t.status,
                    t.status_category,
                    t.priority,
                    t.issue_type,
                    t.assignee,
                    getattr(t, "assignee_avatar", ""),
                    getattr(t, "parent_key", None),
                    getattr(t, "parent_summary", None),
                    getattr(t, "parent_status", None),
                    getattr(t, "parent_issue_type", None),
                    t.created_at.isoformat() if t.created_at else now_iso,
                    t.updated_at.isoformat() if t.updated_at else now_iso,
                    t.html_url,
                    now_iso
                ))
            conn.commit()

    def get_jira_tasks(self) -> List[JiraTaskItem]:
        items: List[JiraTaskItem] = []
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM jira_tasks ORDER BY updated_at DESC")
            for row in cursor.fetchall():
                item = JiraTaskItem(
                    key=row["key"],
                    summary=row["summary"],
                    status=row["status"],
                    status_category=row["status_category"],
                    priority=row["priority"],
                    issue_type=row["issue_type"],
                    assignee=row["assignee"],
                    created_at=self._parse_iso(row["created_at"]) or datetime.now(timezone.utc),
                    updated_at=self._parse_iso(row["updated_at"]) or datetime.now(timezone.utc),
                    html_url=row["html_url"],
                    assignee_avatar=row["assignee_avatar"] or "",
                    parent_key=row["parent_key"],
                    parent_summary=row["parent_summary"],
                    parent_status=row["parent_status"],
                    parent_issue_type=row["parent_issue_type"]
                )
                items.append(item)
        return items

    def save_pull_requests(self, prs: List[PullRequestItem]):
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM pull_requests")
            for pr in prs:
                conn.execute("""
                    INSERT OR REPLACE INTO pull_requests (
                        id, number, title, repo, author, author_avatar, html_url,
                        created_at, updated_at, is_draft, labels, comments_count,
                        review_decision, checks_summary, checks_state, last_synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pr.id,
                    pr.number,
                    pr.title,
                    pr.repo,
                    pr.author,
                    pr.author_avatar,
                    pr.html_url,
                    pr.created_at.isoformat() if pr.created_at else now_iso,
                    pr.updated_at.isoformat() if pr.updated_at else None,
                    1 if pr.is_draft else 0,
                    json.dumps(pr.labels),
                    pr.comments_count,
                    pr.review_decision,
                    getattr(pr, "checks_summary", None),
                    getattr(pr, "checks_state", None),
                    now_iso
                ))
            conn.commit()

    def get_pull_requests(self) -> List[PullRequestItem]:
        items: List[PullRequestItem] = []
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM pull_requests ORDER BY created_at ASC")
            for row in cursor.fetchall():
                labels = []
                if row["labels"]:
                    try:
                        labels = json.loads(row["labels"])
                    except Exception:
                        pass
                review_decision = None
                if "review_decision" in row.keys():
                    review_decision = row["review_decision"]
                checks_summary = row["checks_summary"] if "checks_summary" in row.keys() else None
                checks_state = row["checks_state"] if "checks_state" in row.keys() else None
                item = PullRequestItem(
                    id=row["id"],
                    number=row["number"],
                    title=row["title"],
                    repo=row["repo"],
                    author=row["author"],
                    author_avatar=row["author_avatar"] or "",
                    html_url=row["html_url"],
                    created_at=self._parse_iso(row["created_at"]) or datetime.now(timezone.utc),
                    updated_at=self._parse_iso(row["updated_at"]),
                    is_draft=bool(row["is_draft"]),
                    labels=labels,
                    comments_count=row["comments_count"] or 0,
                    review_decision=review_decision,
                    checks_summary=checks_summary,
                    checks_state=checks_state
                )
                items.append(item)
        return items

    def detect_and_record_new_jira(self, tasks: List[JiraTaskItem]) -> List[JiraTaskItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        new_items: List[JiraTaskItem] = []

        with self._get_connection() as conn:
            cursor = conn.execute("SELECT item_key FROM notifications_seen WHERE item_type = 'jira'")
            known_keys: Set[str] = {row["item_key"] for row in cursor.fetchall()}

            if not known_keys:
                for t in tasks:
                    conn.execute(
                        "INSERT OR IGNORE INTO notifications_seen (item_key, item_type, first_seen_at) VALUES (?, 'jira', ?)",
                        (t.key, now_iso)
                    )
                conn.commit()
                return []

            for t in tasks:
                if t.key not in known_keys:
                    new_items.append(t)
                    conn.execute(
                        "INSERT OR IGNORE INTO notifications_seen (item_key, item_type, first_seen_at) VALUES (?, 'jira', ?)",
                        (t.key, now_iso)
                    )
            conn.commit()

        return new_items

    def detect_and_record_new_prs(self, prs: List[PullRequestItem]) -> List[PullRequestItem]:
        now_iso = datetime.now(timezone.utc).isoformat()
        new_items: List[PullRequestItem] = []

        with self._get_connection() as conn:
            cursor = conn.execute("SELECT item_key FROM notifications_seen WHERE item_type = 'pr'")
            known_ids: Set[str] = {row["item_key"] for row in cursor.fetchall()}

            if not known_ids:
                for pr in prs:
                    conn.execute(
                        "INSERT OR IGNORE INTO notifications_seen (item_key, item_type, first_seen_at) VALUES (?, 'pr', ?)",
                        (str(pr.id), now_iso)
                    )
                conn.commit()
                return []

            for pr in prs:
                if str(pr.id) not in known_ids:
                    new_items.append(pr)
                    conn.execute(
                        "INSERT OR IGNORE INTO notifications_seen (item_key, item_type, first_seen_at) VALUES (?, 'pr', ?)",
                        (str(pr.id), now_iso)
                    )
            conn.commit()

        return new_items

    def add_notification(
        self,
        item_key: str,
        item_type: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> NotificationItem:
        now_dt = created_at or datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notifications (item_key, item_type, title, message, link_url, created_at, is_dismissed)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (item_key, item_type, title, message, link_url, now_iso)
            )
            conn.commit()
            notif_id = cursor.lastrowid
            return NotificationItem(
                id=notif_id,
                item_key=item_key,
                item_type=item_type,
                title=title,
                message=message,
                link_url=link_url,
                created_at=now_dt,
                is_dismissed=False
            )

    def get_active_notifications(self) -> List[NotificationItem]:
        """
        Retorna todas as notificações não removidas ordenadas da mais nova para a mais antiga.
        """
        items: List[NotificationItem] = []
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, item_key, item_type, title, message, link_url, created_at, is_dismissed
                FROM notifications
                WHERE is_dismissed = 0
                ORDER BY created_at DESC, id DESC
                """
            )
            for row in cursor.fetchall():
                created_dt = self._parse_iso(row["created_at"]) or datetime.now(timezone.utc)
                item = NotificationItem(
                    id=row["id"],
                    item_key=row["item_key"],
                    item_type=row["item_type"],
                    title=row["title"],
                    message=row["message"],
                    link_url=row["link_url"],
                    created_at=created_dt,
                    is_dismissed=bool(row["is_dismissed"])
                )
                items.append(item)
        return items

    def dismiss_notification(self, notification_id: int):
        """
        Marca uma notificação como removida para que não seja mais exibida.
        """
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE notifications SET is_dismissed = 1 WHERE id = ?",
                (notification_id,)
            )
            conn.commit()

    def dismiss_all_notifications(self):
        """
        Marca todas as notificações ativas como removidas para que não sejam mais exibidas.
        """
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE notifications SET is_dismissed = 1 WHERE is_dismissed = 0"
            )
            conn.commit()
