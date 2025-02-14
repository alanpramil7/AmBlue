import sqlite3
from datetime import datetime


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
                  task_id TEXT,
                  url TEXT,
                  status TEXT,
                  created_at TIMESTAMP,
                  uodated_at TIMESTAMP
                )
              """)

    def add_task(self, task_id: str, url: str, status: str):
        """"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO website_tasks VALUES (?, ?, ?, ?, ?)",
                (task_id, url, status, datetime.now(), datetime.now()),
            )

    def get_task_by_id(self, task_id: str):
        """"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            res = cur.execute("SELECT * FROM website_tasks WHERE task_id=?", task_id)
            return res.fetchall()

    def get_task_by_url(self, url: str):
        """"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            res = cur.execute("SELECT * FROM website_tasks WHERE url=?", (url,))
            return res.fetchone()
