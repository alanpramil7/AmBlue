import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.types.website import ProcessingStatus, TaskStatus


class DatabaseService:
    """"""

    def __init__(self):
        self._db_path = "data/rag.db"
        self.is_initialized: bool = False

        self.initialize()

    def initialize(self):
        """"""
        if not self.is_initialized:
            self._initialize_tables()
            self.is_initialized = True

    def get_connection(self):
        """"""
        return sqlite3.connect(self._db_path)

    def _initialize_tables(self):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS website_tasks(
                    task_id TEXT PRIMARY KEY,
                    url TEXT,
                    status TEXT,
                    total_urls INTEGER,
                    processed_urls TEXT,
                    remaining_urls TEXT,
                    failed_urls TEXT,
                    current_url TEXT,
                    percent_complete REAL,
                    error TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)

    def add_task(self, task_id: str, url: str, status: str) -> None:
        """Add a basic task record (used by website route)"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO website_tasks 
                (task_id, url, status, total_urls, processed_urls, remaining_urls,
                failed_urls, current_url, percent_complete, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    url,
                    status,
                    0,  # total_urls
                    "",  # processed_urls
                    "",  # remaining_urls
                    "",  # failed_urls
                    None,  # current_url
                    0,  # percent_complete
                    None,  # error
                    datetime.utcnow(),
                    datetime.utcnow(),
                ),
            )

    def create_processing_task(self, task_id: str, url: str) -> None:
        """Create a full processing task record (used by website service)"""
        status = ProcessingStatus()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO website_tasks 
                (task_id, url, status, total_urls, processed_urls, remaining_urls, 
                failed_urls, current_url, percent_complete, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    url,
                    TaskStatus.PENDING.value,
                    status.total_urls,
                    "",  # Empty lists stored as empty strings
                    "",
                    "",
                    status.current_url,
                    status.percent_complete,
                    status.error,
                    datetime.utcnow(),
                    datetime.utcnow(),
                ),
            )

    def update_task_status(self, task_id: str, status: ProcessingStatus) -> None:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE website_tasks 
                SET status = ?, total_urls = ?, processed_urls = ?, remaining_urls = ?,
                failed_urls = ?, current_url = ?, percent_complete = ?, error = ?,
                updated_at = ?
                WHERE task_id = ?""",
                (
                    status.status.value,
                    status.total_urls,
                    ",".join(status.processed_urls),
                    ",".join(status.remaining_urls),
                    ",".join(status.failed_urls),
                    status.current_url,
                    status.percent_complete,
                    status.error,
                    datetime.utcnow(),
                    task_id,
                ),
            )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM website_tasks WHERE task_id = ?", (task_id,))
            row = cur.fetchone()
            if not row:
                return None

            return {
                "task_id": row[0],
                "url": row[1],
                "status": {
                    "status": TaskStatus(row[2]),
                    "total_urls": row[3],
                    "processed_urls": row[4].split(",") if row[4] else [],
                    "remaining_urls": row[5].split(",") if row[5] else [],
                    "failed_urls": row[6].split(",") if row[6] else [],
                    "current_url": row[7],
                    "percent_complete": row[8],
                    "error": row[9],
                },
                "created_at": datetime.fromisoformat(row[10]),
                "updated_at": datetime.fromisoformat(row[11]),
            }

    def get_task_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM website_tasks WHERE url = ?", (url,))
            row = cur.fetchone()
            if not row:
                return None

            return {"task_id": row[0], "url": row[1], "status": row[2]}
