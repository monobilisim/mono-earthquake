import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EarthquakeDatabase:
    """
    Thread-safe SQLite database manager for earthquake data.
    Handles database initialization, data insertion, and queries.
    """

    # Thread-local storage for database connections
    _thread_local = threading.local()

    def __init__(self, db_path: str = "data/earthquakes.db"):
        """
        Initialize the database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)

        # Ensure the directory exists
        self.db_path.parent.mkdir(exist_ok=True, parents=True)

        # Store the db_path for later connection creation
        self._db_path = str(db_path)

        # Connect to database and initialize schema
        conn = self._get_connection()
        self._initialize_schema(conn)

    def _get_connection(self):
        """
        Get a database connection for the current thread.

        Returns:
            sqlite3.Connection: Database connection
        """
        if not hasattr(self._thread_local, "conn"):
            try:
                self._thread_local.conn = sqlite3.connect(
                    self._db_path,
                    check_same_thread=False,
                    timeout=30.0
                )
                self._thread_local.conn.row_factory = sqlite3.Row
                logger.debug(f"Created new database connection in thread {threading.get_ident()}")
            except sqlite3.Error as e:
                logger.error(f"Error creating database connection: {e}")
                raise Exception(f"Error creating database connection: {e}")

        return self._thread_local.conn

    def _initialize_schema(self, conn):
        """
        Create tables if they don't exist.

        Args:
            conn: SQLite connection object
        """
        try:
            cursor = conn.cursor()

            # Create earthquakes table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS earthquakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                depth REAL NOT NULL,
                md REAL,
                ml REAL,
                mw REAL,
                magnitude REAL,
                location TEXT NOT NULL,
                quality TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                week INTEGER NOT NULL,
                UNIQUE(timestamp, latitude, longitude)
            )
            ''')

            # Create index on date for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_earthquakes_date ON earthquakes(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_earthquakes_year_month ON earthquakes(year, month)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_earthquakes_year_week ON earthquakes(year, week)')

            # Create webhooks table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS webhooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                url TEXT NOT NULL,
                type VARCHAR(255) NOT NULL,
                last_sent_at DATETIME,
                created_at TEXT NOT NULL,
                UNIQUE(url),
                UNIQUE(name)
            )
            ''')

            # Create index on webhook name for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_webhooks_name ON webhooks(name)')

            # Create polls table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL UNIQUE,
                type VARCHAR(255) NOT NULL,
                min_magnitude REAL DEFAULT 1.7,
                created_at TEXT NOT NULL
            )
            ''')

            # Create wa_users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS wa_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                phone_number VARCHAR(20) NOT NULL UNIQUE,
                poll_name VARCHAR(255) DEFAULT NULL,
                last_sent_at DATETIME,
                created_at TEXT NOT NULL
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS wa_messages (
                id TEXT PRIMARY KEY,
                wa_user_id INTEGER NOT NULL,
                is_read BOOLEAN NOT NULL DEFAULT 0,
                message TEXT,
                poll_name VARCHAR(255) DEFAULT NULL,
                updated_at DATETIME NOT NULL,
                created_at TEXT NOT NULL
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                poll_name VARCHAR(255) DEFAULT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT NOT NULL UNIQUE,
                expiration_date DATETIME NOT NULL DEFAULT (DATETIME('now', '+7 days')),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            ''')

            # ON DELETE CASCADE does not work if foreign keys are not enabled
            cursor.execute("PRAGMA foreign_keys = ON;")

            cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS delete_expired_sessions
            AFTER INSERT ON sessions
            FOR EACH ROW
            BEGIN
                DELETE FROM sessions WHERE expiration_date <= CURRENT_TIMESTAMP;
            END;
            ''')

            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS keep_last_sessions
                AFTER INSERT ON sessions
                FOR EACH ROW
                BEGIN
                    DELETE FROM sessions
                    WHERE user_id = NEW.user_id
                      AND id NOT IN (
                          SELECT id
                          FROM sessions
                          WHERE user_id = NEW.user_id
                          ORDER BY id DESC
                          LIMIT 1
                      );
                END;
            ''')

            # Create indexes for polls tables
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_polls_name ON polls(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_wa_users_phone ON wa_users(phone_number)')

            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error initializing database schema: {e}")
            raise Exception(f"Error initializing database schema: {e}")

    def clear_old_wa_messages(self):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get all messages - no join needed since poll_name is in wa_messages
            cursor.execute('''
                SELECT id, poll_name, wa_user_id, created_at
                FROM wa_messages
                ORDER BY poll_name, wa_user_id, created_at DESC
            ''')
            all_messages = cursor.fetchall()

            # Group messages by (poll_name, wa_user_id) and keep only the latest
            messages_to_keep = set()
            seen_combinations = set()

            for msg_id, poll_name, wa_user_id, created_at in all_messages:
                combination = (poll_name, wa_user_id)
                if combination not in seen_combinations:
                    messages_to_keep.add(msg_id)
                    seen_combinations.add(combination)

            # Delete messages not in the keep set
            if messages_to_keep:
                placeholders = ','.join('?' * len(messages_to_keep))
                cursor.execute(f'''
                    DELETE FROM wa_messages
                    WHERE id NOT IN ({placeholders})
                ''', list(messages_to_keep))
            else:
                cursor.execute('DELETE FROM wa_messages')

            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleared {deleted_count} WhatsApp messages, keeping last message per user per poll")

        except sqlite3.Error as e:
            logger.error(f"Error clearing old WhatsApp messages: {e}")
            raise Exception(f"Error clearing old WhatsApp messages: {e}")

    def authenticate_user(self, name, password, session=None):
        if session is not None:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM sessions WHERE session_token = ?", (session,))
            user_id = cursor.fetchone()
            return user_id[0]

        if not name or not password:
            return None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE name = ? AND password = ?", (name, password))
            user = cursor.fetchone()
            if user:
                return user[0]  # Return user ID
            return None

        except sqlite3.Error as e:
            logger.error(f"Error authenticating user: {e}")
            raise Exception(f"Error authenticating user: {e}")

    def create_user(self, name, password, poll_name=None):
        if not name or not password:
            return None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, password, poll_name) VALUES (?, ?, ?)", (name, password, poll_name))
            user_id = cursor.lastrowid
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error creating user: {e}")
            raise Exception(f"Error creating user: {e}")

    def create_session(self, user_id, session_token):
        if not user_id or not session_token:
            return None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sessions (user_id, session_token) VALUES (?, ?)", (user_id, session_token))
            session_id = cursor.lastrowid
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error creating session: {e}")
            raise Exception(f"Error creating session: {e}")

    def check_session(self, session_token):
        if not session_token:
            return False
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.session_token
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ?
                AND s.expiration_date > CURRENT_TIMESTAMP
            """, (session_token,))
            session = cursor.fetchone()
            return session is not None
        except sqlite3.Error as e:
            logger.error(f"Error checking session: {e}")
            raise Exception(f"Error checking session: {e}")

    def create_wa_message(self, phone_number, message_id, poll_name: str | None =None):
        if not phone_number or not message_id:
            return 0

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Example: Get wa_user_id from another table
            cursor.execute("SELECT id FROM wa_users WHERE phone_number = ?", (phone_number,))
            user = cursor.fetchone()
            if not user:
                logger.error(f"No wa_user found for phone number: {phone_number}")
                return 0

            wa_user_id = user[0]
            now = datetime.utcnow().isoformat()

            cursor.execute('''
                INSERT INTO wa_messages (id, wa_user_id, is_read, message, poll_name, updated_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (message_id, wa_user_id, 0, None, poll_name, now, now))

            conn.commit()
            return cursor.lastrowid

        except sqlite3.Error as e:
            logger.error(f"Error creating WhatsApp message: {e}")
            raise Exception(f"Error creating WhatsApp message: {e}")

    def update_wa_message(self, message_id, is_read = False, message = None):
        if not message_id:
            return 0

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            applied = 0

            if is_read and message is None:
                cursor.execute("UPDATE wa_messages SET is_read = ? WHERE id = ?", (is_read, message_id,))
                applied += 1

            if message is not None:
                cursor.execute("UPDATE wa_messages SET is_read = ?, message = ? WHERE id = ?", (True, message, message_id,))
                applied += 1

            if applied > 0:
                conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Error updating WhatsApp message: {e}")
            raise Exception(f"Error updating WhatsApp message: {e}")

    def get_wa_messages(self, user_id: int | None):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            poll_name = None
            if user_id is not None:
                cursor.execute("SELECT poll_name FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    poll_name = row['poll_name']

            if poll_name is None:
                wa_messages = cursor.execute('''
                    SELECT wa_users.name as name, wa_users.phone_number as number, wa_messages.message as message, wa_messages.is_read as is_read, wa_messages.created_at as created_at, wa_messages.poll_name as poll_name
                    FROM wa_messages
                    JOIN wa_users ON wa_messages.wa_user_id = wa_users.id
                    LIMIT 1000
                ''')
            else:
                wa_messages = cursor.execute('''
                    SELECT wa_users.name as name, wa_users.phone_number as number, wa_messages.message as message, wa_messages.is_read as is_read, wa_messages.created_at as created_at
                    FROM wa_messages
                    JOIN wa_users ON wa_messages.wa_user_id = wa_users.id
                    WHERE wa_messages.poll_name = ?
                    LIMIT 1000
                ''', (poll_name,))

            return [dict(row) for row in wa_messages]

        except sqlite3.Error as e:
            logger.error(f"Error fetching WhatsApp messages: {e}")
            raise Exception(f"Error fetching WhatsApp messages: {e}")

    def insert_earthquakes(self, earthquakes: List[Dict[str, Any]]) -> int:
        """
        Insert multiple earthquakes into the database.

        Args:
            earthquakes: List of earthquake dictionaries

        Returns:
            Number of earthquakes inserted
        """
        if not earthquakes:
            return 0

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            inserted_count = 0
            for earthquake in earthquakes:
                try:
                    # Parse timestamp to extract date components
                    timestamp = datetime.fromisoformat(earthquake['timestamp'].replace('Z', '+00:00'))
                    year = timestamp.year
                    month = timestamp.month
                    day = timestamp.day
                    week = timestamp.isocalendar()[1]

                    cursor.execute('SELECT 1 FROM earthquakes WHERE timestamp = ?', (earthquake['timestamp'],))
                    if cursor.fetchone():
                        continue

                    cursor.execute('''
                    INSERT OR IGNORE INTO earthquakes (
                        timestamp, date, time, latitude, longitude, depth, md, ml, mw, magnitude, location, quality, year, month, day, week
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        earthquake['timestamp'],
                        earthquake['date'],
                        earthquake['time'],
                        earthquake['latitude'],
                        earthquake['longitude'],
                        earthquake['depth'],
                        earthquake.get('md'),
                        earthquake.get('ml'),
                        earthquake.get('mw'),
                        earthquake.get('magnitude'),
                        earthquake['location'],
                        earthquake['quality'],
                        year,
                        month,
                        day,
                        week
                    ))

                    if cursor.rowcount > 0:
                        inserted_count += 1

                except sqlite3.IntegrityError:
                    # Duplicate entry, skip
                    continue
                except KeyError as e:
                    logger.warning(f"Missing key in earthquake data: {e}")
                    continue

            conn.commit()
            if inserted_count > 0:
                logger.info(f"Inserted {inserted_count} new earthquakes")
            return inserted_count

        except sqlite3.Error as e:
            logger.error(f"Error inserting earthquakes: {e}")
            raise Exception(f"Error inserting earthquakes: {e}")

    def get_latest_earthquakes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the latest earthquakes from the database.

        Args:
            limit: Maximum number of earthquakes to return

        Returns:
            List of earthquake dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT * FROM earthquakes
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (limit,))

            earthquakes = cursor.fetchall()
            return [self.convert_row_to_dict(earthquake) for earthquake in earthquakes]

        except sqlite3.Error as e:
            logger.error(f"Error fetching latest earthquakes: {e}")
            raise Exception(f"Error fetching latest earthquakes: {e}")

    def get_earthquakes_by_date(self, date: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get earthquakes for a specific date.

        Args:
            date: Date in YYYY-MM-DD format
            limit: Maximum number of earthquakes to return

        Returns:
            List of earthquake dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT * FROM earthquakes
            WHERE date = ?
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (date, limit))

            earthquakes = cursor.fetchall()
            return [self.convert_row_to_dict(earthquake) for earthquake in earthquakes]

        except sqlite3.Error as e:
            logger.error(f"Error fetching earthquakes by date: {e}")
            raise Exception(f"Error fetching earthquakes by date: {e}")

    def get_earthquakes_by_week(self, year: int, week: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get earthquakes for a specific week.

        Args:
            year: Year
            week: Week number (1-53)
            limit: Maximum number of earthquakes to return

        Returns:
            List of earthquake dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT * FROM earthquakes
            WHERE year = ? AND week = ?
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (year, week, limit))

            earthquakes = cursor.fetchall()
            return [self.convert_row_to_dict(earthquake) for earthquake in earthquakes]

        except sqlite3.Error as e:
            logger.error(f"Error fetching earthquakes by week: {e}")
            raise Exception(f"Error fetching earthquakes by week: {e}")

    def get_earthquakes_by_month(self, year: int, month: int, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Get earthquakes for a specific month.

        Args:
            year: Year
            month: Month (1-12)
            limit: Maximum number of earthquakes to return

        Returns:
            List of earthquake dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT * FROM earthquakes
            WHERE year = ? AND month = ?
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (year, month, limit))

            earthquakes = cursor.fetchall()
            return [self.convert_row_to_dict(earthquake) for earthquake in earthquakes]

        except sqlite3.Error as e:
            logger.error(f"Error fetching earthquakes by month: {e}")
            raise Exception(f"Error fetching earthquakes by month: {e}")

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics about the earthquake database.

        Returns:
            Dictionary containing summary statistics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get total count
            cursor.execute('SELECT COUNT(*) FROM earthquakes')
            total_count = cursor.fetchone()[0]

            # Get count by magnitude ranges
            cursor.execute('''
            SELECT
                COUNT(CASE WHEN magnitude >= 5.0 THEN 1 END) as major_count,
                COUNT(CASE WHEN magnitude >= 4.0 AND magnitude < 5.0 THEN 1 END) as moderate_count,
                COUNT(CASE WHEN magnitude >= 3.0 AND magnitude < 4.0 THEN 1 END) as minor_count,
                COUNT(CASE WHEN magnitude < 3.0 THEN 1 END) as micro_count
            FROM earthquakes
            WHERE magnitude IS NOT NULL
            ''')

            magnitude_stats = cursor.fetchone()

            # Get latest earthquake
            cursor.execute('SELECT * FROM earthquakes ORDER BY timestamp DESC LIMIT 1')
            latest_earthquake = cursor.fetchone()

            # Get date range
            cursor.execute('SELECT MIN(date), MAX(date) FROM earthquakes')
            date_range = cursor.fetchone()

            return {
                'total_count': total_count,
                'major_earthquakes': magnitude_stats[0] if magnitude_stats else 0,
                'moderate_earthquakes': magnitude_stats[1] if magnitude_stats else 0,
                'minor_earthquakes': magnitude_stats[2] if magnitude_stats else 0,
                'micro_earthquakes': magnitude_stats[3] if magnitude_stats else 0,
                'latest_earthquake': self.convert_row_to_dict(latest_earthquake) if latest_earthquake else None,
                'date_range': {
                    'start': date_range[0] if date_range else None,
                    'end': date_range[1] if date_range else None
                }
            }

        except sqlite3.Error as e:
            logger.error(f"Error getting summary statistics: {e}")
            raise Exception(f"Error getting summary statistics: {e}")

    def convert_row_to_dict(self, row) -> Dict[str, Any]:
        """
        Convert a database row to a dictionary.

        Args:
            row: Database row object

        Returns:
            Dictionary representation of the row
        """
        if row is None:
            return {}
        return dict(row)

    def search_earthquakes(self, min_magnitude: Optional[float] = None,
                         max_magnitude: Optional[float] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         location: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search earthquakes with various filters.

        Args:
            min_magnitude: Minimum magnitude filter
            max_magnitude: Maximum magnitude filter
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            location: Location filter (partial match)
            limit: Maximum number of results

        Returns:
            List of earthquake dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Build dynamic query
            query = "SELECT * FROM earthquakes WHERE 1=1"
            params = []

            if min_magnitude is not None:
                query += " AND magnitude >= ?"
                params.append(min_magnitude)

            if max_magnitude is not None:
                query += " AND magnitude <= ?"
                params.append(max_magnitude)

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            if location:
                query += " AND location LIKE ?"
                params.append(f"%{location}%")

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            earthquakes = cursor.fetchall()

            return [self.convert_row_to_dict(earthquake) for earthquake in earthquakes]

        except sqlite3.Error as e:
            logger.error(f"Error searching earthquakes: {e}")
            raise Exception(f"Error searching earthquakes: {e}")

    def register_webhook(self, name: str, url: str, webhook_type: str) -> int:
        """
        Register a new webhook.

        Args:
            name: Webhook name
            url: Webhook URL
            webhook_type: Type of webhook (discord, zulip, etc.)

        Returns:
            Webhook ID if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            created_at = datetime.now().isoformat()
            cursor.execute('''
            INSERT INTO webhooks (name, url, type, created_at)
            VALUES (?, ?, ?, ?)
            ''', (name, url, webhook_type, created_at))

            conn.commit()
            webhook_id = cursor.lastrowid
            if webhook_id is None:
                raise Exception("Failed to get webhook ID after insert")
            logger.info(f"Registered webhook: {name} ({webhook_type})")
            return webhook_id

        except sqlite3.IntegrityError as e:
            logger.error(f"Webhook registration failed - duplicate name or URL: {e}")
            raise Exception(f"Webhook with name '{name}' or URL '{url}' already exists")
        except sqlite3.Error as e:
            logger.error(f"Error registering webhook: {e}")
            raise Exception(f"Error registering webhook: {e}")

    def update_webhook_last_sent(self, webhook_id: int):
        """
        Update the last sent timestamp for a webhook.

        Args:
            webhook_id: Webhook ID
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            UPDATE webhooks
            SET last_sent_at = datetime()
            WHERE id = ?
            ''', (webhook_id,))

            conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Error updating webhook last sent: {e}")
            raise Exception(f"Error updating webhook last sent: {e}")

    def get_webhook(self, webhook_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific webhook by ID.

        Args:
            webhook_id: Webhook ID

        Returns:
            Webhook dictionary or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id, name, url, type, last_sent_at, created_at
            FROM webhooks
            WHERE id = ?
            ''', (webhook_id,))

            webhook = cursor.fetchone()
            return self.convert_row_to_dict(webhook) if webhook else None

        except sqlite3.Error as e:
            logger.error(f"Error fetching webhook: {e}")
            raise Exception(f"Error fetching webhook: {e}")

    def get_webhooks(self) -> List[Dict[str, Any]]:
        """
        Get all webhooks.

        Returns:
            List of webhook dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id, name, url, type, last_sent_at, created_at
            FROM webhooks
            ORDER BY name
            ''')

            webhooks = cursor.fetchall()
            return [self.convert_row_to_dict(webhook) for webhook in webhooks]

        except sqlite3.Error as e:
            logger.error(f"Error fetching webhooks: {e}")
            raise Exception(f"Error fetching webhooks: {e}")

    def delete_webhook(self, webhook_id: int) -> bool:
        """
        Delete a webhook by ID.

        Args:
            webhook_id: Webhook ID

        Returns:
            True if webhook was deleted, False if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM webhooks WHERE id = ?', (webhook_id,))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Deleted webhook with ID: {webhook_id}")
                return True
            else:
                logger.warning(f"No webhook found with ID: {webhook_id}")
                return False

        except sqlite3.Error as e:
            logger.error(f"Error deleting webhook: {e}")
            raise Exception(f"Error deleting webhook: {e}")

    def create_poll(self, name: str, poll_type: str, min_magnitude: float = 1.7) -> int:
        """
        Create a new poll.

        Args:
            name: Poll name
            poll_type: Type of poll
            min_magnitude: Minimum magnitude threshold

        Returns:
            Poll ID if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            created_at = datetime.now().isoformat()
            cursor.execute('''
            INSERT INTO polls (name, type, min_magnitude, created_at)
            VALUES (?, ?, ?, ?)
            ''', (name, poll_type, min_magnitude, created_at))

            conn.commit()
            poll_id = cursor.lastrowid
            if poll_id is None:
                raise Exception("Failed to get poll ID after insert")
            logger.info(f"Created poll: {name} ({poll_type})")
            return poll_id

        except sqlite3.IntegrityError as e:
            logger.error(f"Poll creation failed - duplicate name: {e}")
            raise Exception(f"Poll with name '{name}' already exists")
        except sqlite3.Error as e:
            logger.error(f"Error creating poll: {e}")
            raise Exception(f"Error creating poll: {e}")

    def get_polls(self) -> List[Dict[str, Any]]:
        """
        Get all polls.

        Returns:
            List of poll dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id, name, type, min_magnitude, created_at
            FROM polls
            ORDER BY name
            ''')

            polls = cursor.fetchall()
            return [self.convert_row_to_dict(poll) for poll in polls]

        except sqlite3.Error as e:
            logger.error(f"Error fetching polls: {e}")
            raise Exception(f"Error fetching polls: {e}")

    def get_poll_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific poll by name.

        Args:
            name: Poll name

        Returns:
            Poll dictionary or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id, name, type, min_magnitude, created_at
            FROM polls
            WHERE name = ?
            ''', (name,))

            poll = cursor.fetchone()
            return self.convert_row_to_dict(poll) if poll else None

        except sqlite3.Error as e:
            logger.error(f"Error fetching poll by name: {e}")
            raise Exception(f"Error fetching poll by name: {e}")

    def delete_poll(self, poll_id: int) -> bool:
        """
        Delete a poll by ID.

        Args:
            poll_id: Poll ID

        Returns:
            True if poll was deleted, False if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM polls WHERE id = ?', (poll_id,))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Deleted poll with ID: {poll_id}")
                return True
            else:
                logger.warning(f"No poll found with ID: {poll_id}")
                return False

        except sqlite3.Error as e:
            logger.error(f"Error deleting poll: {e}")
            raise Exception(f"Error deleting poll: {e}")

    def create_wa_user(self, name: str, phone_number: str, poll_name: str | None) -> int:
        """
        Create a new WhatsApp user.

        Args:
            name: User name
            phone_number: Phone number

        Returns:
            User ID if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            created_at = datetime.now().isoformat()
            cursor.execute('''
            INSERT INTO wa_users (name, phone_number, poll_name, created_at)
            VALUES (?, ?, ?, ?)
            ''', (name, phone_number, poll_name, created_at))

            conn.commit()
            user_id = cursor.lastrowid
            if user_id is None:
                raise Exception("Failed to get user ID after insert")
            logger.info(f"Created WhatsApp user: {name} ({phone_number})")
            return user_id

        except sqlite3.Error as e:
            logger.error(f"Error creating WhatsApp user: {e}")
            raise Exception(f"Error creating WhatsApp user: {e}")

    def get_wa_users(self) -> List[Dict[str, Any]]:
        """
        Get all WhatsApp users.

        Returns:
            List of user dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id, name, phone_number, poll_name, last_sent_at, created_at
            FROM wa_users
            ORDER BY name
            ''')

            users = cursor.fetchall()
            return [self.convert_row_to_dict(user) for user in users]

        except sqlite3.Error as e:
            logger.error(f"Error fetching WhatsApp users: {e}")
            raise Exception(f"Error fetching WhatsApp users: {e}")

    def update_wa_user_last_sent(self, phone_number: str):
        """
        Update the last sent timestamp for a WhatsApp user.

        Args:
            phone_number: User's phone number
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            UPDATE wa_users
            SET last_sent_at = datetime()
            WHERE phone_number = ?
            ''', (phone_number,))

            conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Error updating WhatsApp user last sent: {e}")
            raise Exception(f"Error updating WhatsApp user last sent: {e}")

    def delete_last_earthquake(self):
        """
        Delete the most recent earthquake from the database.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            DELETE FROM earthquakes
            WHERE id = (
                SELECT id FROM earthquakes
                ORDER BY timestamp DESC
                LIMIT 1
            )
            ''')

            conn.commit()
            if cursor.rowcount > 0:
                logger.info("Deleted the most recent earthquake")
            else:
                logger.warning("No earthquakes found to delete")

        except sqlite3.Error as e:
            logger.error(f"Error deleting last earthquake: {e}")
            raise Exception(f"Error deleting last earthquake: {e}")

    def close(self):
        """Close the database connection for the current thread."""
        if hasattr(self._thread_local, "conn"):
            try:
                self._thread_local.conn.close()
                delattr(self._thread_local, "conn")
                logger.debug(f"Closed database connection in thread {threading.get_ident()}")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}")
