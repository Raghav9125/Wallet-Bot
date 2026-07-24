import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SERVICES = [
    ("google_pay", "Google Pay Business", 1500),
    ("bharatpe", "BharatPe Business", 1000),
    ("mobikwik", "MobiKwik Business", 1000),
    ("phonepe", "PhonePe Business", 1000),
    ("bajaj_pay", "Bajaj Pay Business", 1000),
    ("paytm", "Paytm Business", 1000),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS services (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price INTEGER NOT NULL CHECK(price >= 0),
                    active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_no TEXT UNIQUE,
                    user_id INTEGER NOT NULL,
                    full_name TEXT NOT NULL,
                    username TEXT,
                    service_code TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    receipt_file_id TEXT NOT NULL,
                    utr TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'PAYMENT_PENDING',
                    admin_note TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_app_user ON applications(user_id);
                CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status);
                """
            )

            for code, name, price in DEFAULT_SERVICES:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO services(code, name, price, active)
                    VALUES (?, ?, ?, 1)
                    """,
                    (code, name, price),
                )

            defaults = {
                "whatsapp_link": "https://wa.me/",
                "channel_link": "https://t.me/",
                "upi_id": "Not set",
                "payment_name": "India Business Wallet",
                "qr_file_id": "",
                "support_text": "Hamari support team se WhatsApp par sampark karein.",
            }
            for key, value in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                    (key, value),
                )

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def list_services(self, active_only: bool = True):
        query = "SELECT * FROM services"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY name"
        with self.connect() as conn:
            return conn.execute(query).fetchall()

    def get_service(self, code: str):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM services WHERE code = ? AND active = 1", (code,)
            ).fetchone()

    def update_service_price(self, code: str, price: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE services SET price = ? WHERE code = ?", (price, code)
            )
            return cur.rowcount > 0

    def application_exists_by_utr(self, utr: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM applications WHERE UPPER(utr) = UPPER(?)", (utr,)
            ).fetchone()
            return row is not None

    def create_application(
        self,
        user_id: int,
        full_name: str,
        username: str | None,
        service_code: str,
        service_name: str,
        amount: int,
        receipt_file_id: str,
        utr: str,
    ) -> str:
        now = utc_now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO applications(
                    application_no, user_id, full_name, username,
                    service_code, service_name, amount, receipt_file_id,
                    utr, status, created_at, updated_at
                ) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, 'PAYMENT_PENDING', ?, ?)
                """,
                (
                    user_id,
                    full_name,
                    username,
                    service_code,
                    service_name,
                    amount,
                    receipt_file_id,
                    utr,
                    now,
                    now,
                ),
            )
            app_id = cur.lastrowid
            app_no = f"IBW-{datetime.now().strftime('%y%m%d')}-{app_id:05d}"
            conn.execute(
                "UPDATE applications SET application_no = ? WHERE id = ?",
                (app_no, app_id),
            )
            return app_no

    def get_application(self, application_no: str):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM applications WHERE application_no = ?",
                (application_no,),
            ).fetchone()

    def get_user_applications(self, user_id: int, limit: int = 10):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM applications
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

    def list_applications(self, status: str | None = None, limit: int = 30):
        with self.connect() as conn:
            if status:
                return conn.execute(
                    """
                    SELECT * FROM applications
                    WHERE status = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            return conn.execute(
                "SELECT * FROM applications ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

    def update_application_status(
        self, application_no: str, status: str, admin_note: str | None = None
    ) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE applications
                SET status = ?, admin_note = ?, updated_at = ?
                WHERE application_no = ?
                """,
                (status, admin_note, utc_now(), application_no),
            )
            return cur.rowcount > 0

    def stats(self) -> dict[str, int]:
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM applications").fetchone()["c"]
            pending = conn.execute(
                "SELECT COUNT(*) AS c FROM applications WHERE status = 'PAYMENT_PENDING'"
            ).fetchone()["c"]
            success = conn.execute(
                "SELECT COUNT(*) AS c FROM applications WHERE status = 'SUCCESS'"
            ).fetchone()["c"]
            rejected = conn.execute(
                "SELECT COUNT(*) AS c FROM applications WHERE status = 'REJECTED'"
            ).fetchone()["c"]
            return {
                "total": total,
                "pending": pending,
                "success": success,
                "rejected": rejected,
            }
