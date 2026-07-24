import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SERVICES = [
    ('google_pay', 'Google Pay Business', 1500),
    ('bharatpe', 'BharatPe Business', 1000),
    ('mobikwik', 'MobiKwik Business', 1000),
    ('phonepe', 'PhonePe Business', 1000),
    ('bajaj_pay', 'Bajaj Pay Business', 1000),
    ('paytm', 'Paytm Business', 1000),
]

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

class Database:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _column_names(self, conn, table: str) -> set[str]:
        return {r['name'] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}

    def _add_column_if_missing(self, conn, table: str, name: str, definition: str) -> None:
        if name not in self._column_names(conn, table):
            conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript('''
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
                    receipt_file_id TEXT,
                    utr TEXT UNIQUE,
                    status TEXT NOT NULL DEFAULT 'FIRST_PAYMENT_PENDING',
                    admin_note TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_app_user ON applications(user_id);
                CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status);
            ''')
            # Safe migration from old one-payment database.
            additions = {
                'first_amount': 'INTEGER NOT NULL DEFAULT 0',
                'remaining_amount': 'INTEGER NOT NULL DEFAULT 0',
                'first_receipt_file_id': 'TEXT',
                'first_utr': 'TEXT',
                'final_receipt_file_id': 'TEXT',
                'final_utr': 'TEXT',
                'final_payment_requested_at': 'TEXT',
            }
            for name, definition in additions.items():
                self._add_column_if_missing(conn, 'applications', name, definition)

            for code, name, price in DEFAULT_SERVICES:
                conn.execute('INSERT OR IGNORE INTO services(code,name,price,active) VALUES(?,?,?,1)', (code,name,price))

            defaults = {
                'whatsapp_link': 'https://wa.me/',
                'channel_link': 'https://t.me/',
                'welcome_image_file_id': '',
                'support_text': 'Hamari support team se WhatsApp ya Email par sampark karein.',
                'support_email': 'support@example.com',
                'first_payment_qr_file_id': '',
                'first_payment_banking_name': 'India Business Wallet',
            }
            for code, _, _ in DEFAULT_SERVICES:
                defaults[f'final_qr_{code}'] = ''
                defaults[f'final_banking_name_{code}'] = 'India Business Wallet'
            for key, value in defaults.items():
                conn.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)', (key,value))

    def get_setting(self, key: str, default: str='') -> str:
        with self.connect() as conn:
            row = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return row['value'] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key,value))

    def list_services(self, active_only: bool=True):
        q = 'SELECT * FROM services'
        if active_only: q += ' WHERE active=1'
        q += ' ORDER BY name'
        with self.connect() as conn: return conn.execute(q).fetchall()

    def get_service(self, code: str, active_only: bool=False):
        q = 'SELECT * FROM services WHERE code=?'
        if active_only: q += ' AND active=1'
        with self.connect() as conn: return conn.execute(q,(code,)).fetchone()

    def update_service_price(self, code: str, price: int) -> bool:
        with self.connect() as conn:
            return conn.execute('UPDATE services SET price=? WHERE code=?',(price,code)).rowcount > 0

    def set_service_active(self, code: str, active: bool) -> bool:
        with self.connect() as conn:
            return conn.execute('UPDATE services SET active=? WHERE code=?',(1 if active else 0, code)).rowcount > 0

    def utr_exists(self, utr: str) -> bool:
        with self.connect() as conn:
            row = conn.execute('SELECT 1 FROM applications WHERE UPPER(COALESCE(first_utr, utr, ""))=UPPER(?) OR UPPER(COALESCE(final_utr,""))=UPPER(?)', (utr,utr)).fetchone()
            return row is not None

    def create_application(self, *, user_id:int, full_name:str, username:str|None, service_code:str, service_name:str, amount:int, receipt_file_id:str, utr:str) -> str:
        now = utc_now(); first = amount // 2; remaining = amount - first
        with self.connect() as conn:
            cur = conn.execute('''
                INSERT INTO applications(application_no,user_id,full_name,username,service_code,service_name,amount,
                  receipt_file_id,utr,status,admin_note,created_at,updated_at,first_amount,remaining_amount,first_receipt_file_id,first_utr)
                VALUES(NULL,?,?,?,?,?,?,?,?,'FIRST_PAYMENT_PENDING',NULL,?,?,?,?,?,?)
            ''', (user_id,full_name,username,service_code,service_name,amount,receipt_file_id,utr,now,now,first,remaining,receipt_file_id,utr))
            app_id = cur.lastrowid
            app_no = f"IBW-{datetime.now().strftime('%y%m%d')}-{app_id:05d}"
            conn.execute('UPDATE applications SET application_no=? WHERE id=?',(app_no,app_id))
            return app_no

    def get_application(self, app_no: str):
        with self.connect() as conn: return conn.execute('SELECT * FROM applications WHERE application_no=?',(app_no,)).fetchone()

    def get_user_applications(self, user_id:int, limit:int=10):
        with self.connect() as conn: return conn.execute('SELECT * FROM applications WHERE user_id=? ORDER BY id DESC LIMIT ?',(user_id,limit)).fetchall()

    def list_applications(self, status:str|None=None, limit:int=30):
        with self.connect() as conn:
            if status:
                return conn.execute('SELECT * FROM applications WHERE status=? ORDER BY id DESC LIMIT ?',(status,limit)).fetchall()
            return conn.execute('SELECT * FROM applications ORDER BY id DESC LIMIT ?',(limit,)).fetchall()

    def update_status(self, app_no:str, status:str, note:str|None=None) -> bool:
        with self.connect() as conn:
            return conn.execute('UPDATE applications SET status=?,admin_note=?,updated_at=? WHERE application_no=?',(status,note,utc_now(),app_no)).rowcount>0

    def request_final_payment(self, app_no:str) -> bool:
        with self.connect() as conn:
            return conn.execute("UPDATE applications SET status='FINAL_PAYMENT_REQUESTED',final_payment_requested_at=?,updated_at=? WHERE application_no=?",(utc_now(),utc_now(),app_no)).rowcount>0

    def submit_final_payment(self, app_no:str, receipt_file_id:str, utr:str) -> bool:
        with self.connect() as conn:
            return conn.execute("UPDATE applications SET final_receipt_file_id=?,final_utr=?,status='FINAL_PAYMENT_PENDING',updated_at=? WHERE application_no=?",(receipt_file_id,utr,utc_now(),app_no)).rowcount>0

    def stats(self):
        with self.connect() as conn:
            def c(status=None):
                if status: return conn.execute('SELECT COUNT(*) c FROM applications WHERE status=?',(status,)).fetchone()['c']
                return conn.execute('SELECT COUNT(*) c FROM applications').fetchone()['c']
            return {'total':c(), 'pending':c('FIRST_PAYMENT_PENDING')+c('FINAL_PAYMENT_PENDING'), 'success':c('SUCCESS'), 'rejected':c('REJECTED')}
