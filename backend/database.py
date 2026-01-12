import sqlite3
import json
import hashlib
from cryptography.fernet import Fernet
import base64


class DatabaseManager:
    def __init__(self, db_name="backend/bot_data.db"):
        self.db_name = db_name
        self._init_db()

        # Enable WAL mode to prevent locking issues and improve concurrency
        try:
            with self._get_connection() as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                # Balanced performance/safety
                conn.execute("PRAGMA synchronous=NORMAL")
        except Exception as e:
            print(f"Error enabling WAL mode: {e}")

    def _get_connection(self):
        """Returns a sqlite3 connection. WAL mode and foreign keys enabled."""
        conn = sqlite3.connect(self.db_name, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _get_encryption_key(self, user_id: str) -> bytes:
        """Generate a deterministic encryption key from user_id"""
        # This creates a key from the user_id - simple but functional
        # For production, consider using a master key from environment
        key_material = hashlib.sha256(
            f"{user_id}_encryption_salt".encode()).digest()
        return base64.urlsafe_b64encode(key_material)

    def _encrypt_value(self, value: str, user_id: str) -> str:
        """Encrypt a value using Fernet"""
        key = self._get_encryption_key(user_id)
        f = Fernet(key)
        return f.encrypt(value.encode()).decode()

    def _decrypt_value(self, encrypted_value: str, user_id: str) -> str:
        """Decrypt a value using Fernet"""
        key = self._get_encryption_key(user_id)
        f = Fernet(key)
        return f.decrypt(encrypted_value.encode()).decode()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    api_key_encrypted TEXT NOT NULL,
                    api_secret_encrypted TEXT NOT NULL,
                    is_testnet INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    session_token TEXT
                )
            ''')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_users_token ON users(session_token)')

            # Table for trades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    time TEXT,
                    type TEXT,
                    price REAL,
                    qty REAL,
                    pnl REAL,
                    symbol TEXT,
                    rsi REAL,
                    commission REAL DEFAULT 0,
                    total REAL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(time)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')

            # Migration: Add user_id column if it doesn't exist
            try:
                cursor.execute(
                    'ALTER TABLE trades ADD COLUMN user_id INTEGER DEFAULT 1')
            except sqlite3.OperationalError:
                pass

            # Migration for existing DBs (other columns)
            try:
                cursor.execute('ALTER TABLE trades ADD COLUMN rsi REAL')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute(
                    'ALTER TABLE trades ADD COLUMN commission REAL DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute(
                    'ALTER TABLE trades ADD COLUMN total REAL DEFAULT 0')
            except sqlite3.OperationalError:
                pass

            # Migrate settings table - backup and recreate with new schema
            try:
                # Check if settings table exists with old schema
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
                if cursor.fetchone():
                    # Check if it has the old schema (no user_id in primary key)
                    cursor.execute("PRAGMA table_info(settings)")
                    columns = [col[1] for col in cursor.fetchall()]

                    if 'user_id' not in columns:
                        # Backup old data
                        cursor.execute(
                            "ALTER TABLE settings RENAME TO settings_old")
                        # Create new table with correct schema
                        cursor.execute('''
                            CREATE TABLE settings (
                                user_id INTEGER DEFAULT 1,
                                key TEXT,
                                value TEXT,
                                PRIMARY KEY (user_id, key),
                                FOREIGN KEY (user_id) REFERENCES users (id)
                            )
                        ''')
                        # Migrate data to new table with default user_id=1
                        cursor.execute('''
                            INSERT INTO settings (user_id, key, value)
                            SELECT 1, key, value FROM settings_old
                        ''')
                        # Drop old table
                        cursor.execute("DROP TABLE settings_old")
                else:
                    # Table doesn't exist, create it
                    cursor.execute('''
                        CREATE TABLE settings (
                            user_id INTEGER DEFAULT 1,
                            key TEXT,
                            value TEXT,
                            PRIMARY KEY (user_id, key),
                            FOREIGN KEY (user_id) REFERENCES users (id)
                        )
                    ''')
            except Exception as e:
                print(f"Settings migration: {e}")
                # If anything fails, just create the table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        user_id INTEGER DEFAULT 1,
                        key TEXT,
                        value TEXT,
                        PRIMARY KEY (user_id, key),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')

            # Migrate state table - backup and recreate with new schema
            try:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='state'")
                if cursor.fetchone():
                    cursor.execute("PRAGMA table_info(state)")
                    columns = [col[1] for col in cursor.fetchall()]

                    if 'user_id' not in columns:
                        cursor.execute("ALTER TABLE state RENAME TO state_old")
                        cursor.execute('''
                            CREATE TABLE state (
                                user_id INTEGER DEFAULT 1,
                                key TEXT,
                                value TEXT,
                                PRIMARY KEY (user_id, key),
                                FOREIGN KEY (user_id) REFERENCES users (id)
                            )
                        ''')
                        cursor.execute('''
                            INSERT INTO state (user_id, key, value)
                            SELECT 1, key, value FROM state_old
                        ''')
                        cursor.execute("DROP TABLE state_old")
                else:
                    cursor.execute('''
                        CREATE TABLE state (
                            user_id INTEGER DEFAULT 1,
                            key TEXT,
                            value TEXT,
                            PRIMARY KEY (user_id, key),
                            FOREIGN KEY (user_id) REFERENCES users (id)
                        )
                    ''')
            except Exception as e:
                print(f"State migration: {e}")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS state (
                        user_id INTEGER DEFAULT 1,
                        key TEXT,
                        value TEXT,
                        PRIMARY KEY (user_id, key),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')

            conn.commit()

    # ========== USER MANAGEMENT ==========

    def create_user(self, username: str, api_key: str, api_secret: str, is_testnet: bool = True) -> int:
        """Create a new user with encrypted API credentials"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # First create user with temp values to get user_id
            cursor.execute('''
                INSERT INTO users (username, api_key_encrypted, api_secret_encrypted, is_testnet)
                VALUES (?, ?, ?, ?)
            ''', (username, 'temp', 'temp', 1 if is_testnet else 0))

            user_id = cursor.lastrowid

            # Now encrypt the credentials using the user_id
            encrypted_key = self._encrypt_value(api_key, str(user_id))
            encrypted_secret = self._encrypt_value(api_secret, str(user_id))

            # Update with encrypted values
            cursor.execute('''
                UPDATE users 
                SET api_key_encrypted = ?, api_secret_encrypted = ?
                WHERE id = ?
            ''', (encrypted_key, encrypted_secret, user_id))

            conn.commit()
            return user_id

    def get_user_by_username(self, username: str):
        """Get user by username"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, api_key_encrypted, api_secret_encrypted, is_testnet, session_token
                FROM users WHERE username = ?
            ''', (username,))
            row = cursor.fetchone()

            if not row:
                return None

            user_id = row[0]
            return {
                'id': user_id,
                'username': row[1],
                'api_key': self._decrypt_value(row[2], str(user_id)),
                'api_secret': self._decrypt_value(row[3], str(user_id)),
                'is_testnet': bool(row[4]),
                'session_token': row[5]
            }

    def get_all_users(self):
        """Get all registered users with decrypted credentials"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, api_key_encrypted, api_secret_encrypted, is_testnet, session_token
                FROM users
            ''')
            rows = cursor.fetchall()

            users = []
            for row in rows:
                user_id = row[0]
                users.append({
                    'id': user_id,
                    'username': row[1],
                    'api_key': self._decrypt_value(row[2], str(user_id)),
                    'api_secret': self._decrypt_value(row[3], str(user_id)),
                    'is_testnet': bool(row[4]),
                    'session_token': row[5]
                })
            return users

    def get_user_by_token(self, token: str):
        """Get user by session token"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, api_key_encrypted, api_secret_encrypted, is_testnet
                FROM users WHERE session_token = ?
            ''', (token,))
            row = cursor.fetchone()

            if not row:
                return None

            user_id = row[0]
            return {
                'id': user_id,
                'username': row[1],
                'api_key': self._decrypt_value(row[2], str(user_id)),
                'api_secret': self._decrypt_value(row[3], str(user_id)),
                'is_testnet': bool(row[4])
            }

    def set_user_session(self, user_id: int, token: str):
        """Set session token for user"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET session_token = ? WHERE id = ?', (token, user_id))
            conn.commit()

    def clear_user_session(self, user_id: int):
        """Clear session token for user"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET session_token = NULL WHERE id = ?', (user_id,))
            conn.commit()

    # ========== TRADES ==========

    def save_trade(self, trade_data: dict, user_id: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (user_id, time, type, price, qty, pnl, symbol, rsi, commission, total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                trade_data.get("time"),
                trade_data.get("type"),
                trade_data.get("price"),
                trade_data.get("qty", 0.0),
                trade_data.get("pnl", 0.0),
                trade_data.get("symbol", "BTCUSDT"),
                trade_data.get("rsi", 0.0),
                trade_data.get("commission", 0.0),
                trade_data.get("total", 0.0)
            ))
            conn.commit()

    def get_trades(self, user_id: int = 1, limit=50):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT time, type, price, pnl, rsi, qty, commission, total, symbol 
                   FROM trades WHERE user_id = ? ORDER BY id DESC LIMIT ?''',
                (user_id, limit)
            )
            rows = cursor.fetchall()
            return [{
                "time": r[0],
                "type": r[1],
                "price": r[2],
                "pnl": r[3],
                "rsi": r[4],
                "qty": r[5],
                "commission": r[6] if len(r) > 6 else 0,
                "total": r[7] if len(r) > 7 else 0,
                "symbol": r[8] if len(r) > 8 else "BTCUSDT"
            } for r in rows]

    def clear_trades(self, user_id: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM trades WHERE user_id = ?', (user_id,))
            conn.commit()

    # ========== SETTINGS ==========

    def save_setting(self, key: str, value, user_id: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)',
                (user_id, key, str(value))
            )
            conn.commit()

    def get_setting(self, key: str, default=None, user_id: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT value FROM settings WHERE user_id = ? AND key = ?', (user_id, key))
            row = cursor.fetchone()
            return row[0] if row else default

    # ========== STATE ==========

    def save_state(self, key: str, value, user_id: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # If value is a dict or list, store as JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            cursor.execute(
                'INSERT OR REPLACE INTO state (user_id, key, value) VALUES (?, ?, ?)',
                (user_id, key, str(value))
            )
            conn.commit()

    def get_state(self, key: str, default=None, is_json=False, user_id: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT value FROM state WHERE user_id = ? AND key = ?', (user_id, key))
            row = cursor.fetchone()
            if not row:
                return default
            val = row[0]
            if is_json:
                try:
                    return json.loads(val)
                except json.JSONDecodeError:
                    return default
            return val
