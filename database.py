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
        Get a thread-specific database connection.
        Creates a new connection if none exists for the current thread.

        Returns:
            SQLite connection object
        """
        # Check if we already have a connection for this thread
        if not hasattr(self._thread_local, "conn"):
            try:
                # Create a new connection for this thread
                conn = sqlite3.connect(self._db_path)
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")
                # Return row results as dictionaries
                conn.row_factory = sqlite3.Row
                # Store connection in thread-local storage
                self._thread_local.conn = conn
                logger.debug(f"Created new database connection in thread {threading.get_ident()}")
            except sqlite3.Error as e:
                logger.error(f"Error creating database connection: {e}")
                raise Exception(f"Error connecting to database: {e}")

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

            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error initializing database schema: {e}")
            raise Exception(f"Error initializing database schema: {e}")

    def insert_earthquakes(self, earthquakes: List[Dict[str, Any]]) -> int:
        """
        Insert multiple earthquake records into the database.

        Args:
            earthquakes: List of earthquake records to insert

        Returns:
            Number of records inserted
        """
        if not earthquakes:
            return 0

        conn = self._get_connection()
        cursor = conn.cursor()
        inserted = 0

        try:
            for eq in earthquakes:
                # First check if the earthquake already exists to avoid consuming IDs
                cursor.execute('''
                SELECT id FROM earthquakes
                WHERE timestamp = ? AND latitude = ? AND longitude = ?
                ''', (eq["timestamp"], eq["latitude"], eq["longitude"]))

                # If it exists, skip the insert attempt completely
                if cursor.fetchone():
                    continue

                # Parse date to extract year, month, day
                eq_date = datetime.strptime(eq["date"], "%Y-%m-%d")
                year, month, day = eq_date.year, eq_date.month, eq_date.day

                # Get week number
                _, week, _ = eq_date.isocalendar()

                cursor.execute('''
                INSERT INTO earthquakes
                (timestamp, date, time, latitude, longitude, depth, md, ml, mw, magnitude,
                location, quality, year, month, day, week)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    eq["timestamp"],
                    eq["date"],
                    eq["time"],
                    eq["latitude"],
                    eq["longitude"],
                    eq["depth"],
                    eq["md"],
                    eq["ml"],
                    eq["mw"],
                    eq["magnitude"],
                    eq["location"],
                    eq["quality"],
                    year,
                    month,
                    day,
                    week
                ))

                inserted += cursor.rowcount

            conn.commit()
            return inserted
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error inserting earthquake data: {e}")
            raise Exception(f"Error inserting earthquake data: {e}")

    def get_latest_earthquakes(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get the latest earthquake records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of the latest earthquake records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM earthquakes
            ORDER BY timestamp DESC
            LIMIT ?
            ''', (limit,))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving latest earthquakes: {e}")
            raise Exception(f"Error retrieving latest earthquakes: {e}")

    def get_earthquakes_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Get earthquake records for a specific date.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            List of earthquake records for the specified date
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM earthquakes
            WHERE date = ?
            ORDER BY timestamp DESC
            ''', (date_str,))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving earthquakes for date {date_str}: {e}")
            raise Exception(f"Error retrieving earthquakes for date {date_str}: {e}")

    def get_earthquakes_by_week(self, year: int, week: int) -> List[Dict[str, Any]]:
        """
        Get earthquake records for a specific week.

        Args:
            year: Year as integer
            week: Week number as integer

        Returns:
            List of earthquake records for the specified week
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM earthquakes
            WHERE year = ? AND week = ?
            ORDER BY timestamp DESC
            ''', (year, week))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving earthquakes for week {week}, {year}: {e}")
            raise Exception(f"Error retrieving earthquakes for week {week}, {year}: {e}")

    def get_earthquakes_by_month(self, year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get earthquake records for a specific month.

        Args:
            year: Year as integer
            month: Month as integer

        Returns:
            List of earthquake records for the specified month
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM earthquakes
            WHERE year = ? AND month = ?
            ORDER BY timestamp DESC
            ''', (year, month))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving earthquakes for month {month}, {year}: {e}")
            raise Exception(f"Error retrieving earthquakes for month {month}, {year}: {e}")

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics about the database.

        Returns:
            Dictionary containing statistics about the earthquake data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Total count
            cursor.execute("SELECT COUNT(*) as count FROM earthquakes")
            total_count = cursor.fetchone()["count"]

            # Date range
            cursor.execute("SELECT MIN(date) as min_date, MAX(date) as max_date FROM earthquakes")
            date_range = cursor.fetchone()

            # Average magnitude
            cursor.execute("SELECT AVG(magnitude) as avg_magnitude FROM earthquakes WHERE magnitude IS NOT NULL")
            avg_magnitude = cursor.fetchone()["avg_magnitude"]

            # Maximum magnitude
            cursor.execute("SELECT MAX(magnitude) as max_magnitude FROM earthquakes WHERE magnitude IS NOT NULL")
            max_magnitude = cursor.fetchone()["max_magnitude"]

            # Count by quality
            cursor.execute("SELECT quality, COUNT(*) as count FROM earthquakes GROUP BY quality")
            quality_counts = {row["quality"]: row["count"] for row in cursor.fetchall()}

            # Recent data (last 24 hours)
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("SELECT COUNT(*) as count FROM earthquakes WHERE timestamp > ?", (yesterday,))
            recent_count = cursor.fetchone()["count"]

            return {
                "total_earthquakes": total_count,
                "date_range": {
                    "first_record": date_range["min_date"] if date_range else None,
                    "last_record": date_range["max_date"] if date_range else None
                },
                "magnitude_stats": {
                    "average": avg_magnitude,
                    "maximum": max_magnitude
                },
                "quality_distribution": quality_counts,
                "last_24_hours": recent_count
            }
        except sqlite3.Error as e:
            logger.error(f"Error retrieving database statistics: {e}")
            raise Exception(f"Error retrieving database statistics: {e}")

    def convert_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary suitable for API responses."""
        data = dict(row)

        # Remove database-specific fields from API response
        if 'id' in data:
            del data['id']
        if 'year' in data:
            del data['year']
        if 'month' in data:
            del data['month']
        if 'day' in data:
            del data['day']
        if 'week' in data:
            del data['week']

        return data

    def search_earthquakes(self,
                          min_magnitude: Optional[float] = None,
                          max_magnitude: Optional[float] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          location_keyword: Optional[str] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for earthquakes based on various criteria.

        Args:
            min_magnitude: Minimum magnitude
            max_magnitude: Maximum magnitude
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            location_keyword: Keyword to search in location field
            limit: Maximum number of records to return

        Returns:
            List of matching earthquake records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM earthquakes WHERE 1=1"
            params = []

            if min_magnitude is not None:
                query += " AND magnitude >= ?"
                params.append(min_magnitude)

            if max_magnitude is not None:
                query += " AND magnitude <= ?"
                params.append(max_magnitude)

            if start_date is not None:
                query += " AND date >= ?"
                params.append(start_date)

            if end_date is not None:
                query += " AND date <= ?"
                params.append(end_date)

            if location_keyword is not None:
                query += " AND location LIKE ?"
                params.append(f"%{location_keyword}%")

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error searching earthquakes: {e}")
            raise Exception(f"Error searching earthquakes: {e}")

    def register_webhook(self, name: str, url: str) -> Optional[int]:
        """
        Register a new webhook.

        Args:
            name: Webhook name
            url: Webhook URL
            type: Webhook type

        Returns:
            ID of the newly created webhook
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get current timestamp in ISO format
            now = datetime.now().isoformat()

            cursor.execute('''
            INSERT OR REPLACE INTO webhooks
            (name, url, created_at)
            VALUES (?, ?, ?)
            ''', (name, url, now))

            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error registering webhook: {e}")
            raise Exception(f"Error registering webhook: {e}")

    def update_webhook_last_sent(self, webhook_id: int) -> bool:
        """
        Update the last_sent_at timestamp for a webhook.

        Args:
            webhook_id: ID of the webhook to update

        Returns:
            True if successful, False if webhook not found
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get current timestamp in ISO format
            now = datetime.now().isoformat()

            cursor.execute('''
            UPDATE webhooks
            SET last_sent_at = ?
            WHERE id = ?
            ''', (now, webhook_id))

            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating webhook last_sent_at: {e}")
            raise Exception(f"Error updating webhook last_sent_at: {e}")

    def get_webhook(self, webhook_id: int) -> Optional[Dict[str, Any]]:
        """
        Get webhook by ID.

        Args:
            webhook_id: ID of the webhook to retrieve

        Returns:
            Dictionary containing webhook data or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT * FROM webhooks
            WHERE id = ?
            ''', (webhook_id,))

            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving webhook: {e}")
            raise Exception(f"Error retrieving webhook: {e}")

    def get_webhooks(self) -> List[Dict[str, Any]]:
        """
        Get all registered webhooks.

        Returns:
            List of dictionaries containing webhook data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT * FROM webhooks
            ORDER BY name ASC
            ''')

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving webhooks: {e}")
            raise Exception(f"Error retrieving webhooks: {e}")

    def delete_webhook(self, webhook_id: int) -> bool:
        """
        Delete a webhook by ID.

        Args:
            webhook_id: ID of the webhook to delete

        Returns:
            True if successful, False if webhook not found
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            DELETE FROM webhooks
            WHERE id = ?
            ''', (webhook_id,))

            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error deleting webhook: {e}")
            raise Exception(f"Error deleting webhook: {e}")

    def close(self):
        """Close the database connection for the current thread."""
        if hasattr(self._thread_local, "conn"):
            try:
                self._thread_local.conn.close()
                delattr(self._thread_local, "conn")
                logger.debug(f"Closed database connection in thread {threading.get_ident()}")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}")
