"""
Database module for Philadelphia Events Calendar
Supports both SQLite (local) and PostgreSQL (cloud)
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EventDatabase:
    """Database handler supporting SQLite and PostgreSQL"""

    def __init__(self, db_path: str = "events.db", use_postgres: bool = False):
        self.db_path = db_path
        self.use_postgres = use_postgres

        if use_postgres:
            self.setup_postgres()
        else:
            self.init_sqlite_database()

    def setup_postgres(self):
        """Setup PostgreSQL connection (for cloud deployment)"""
        try:
            import psycopg2
            from psycopg2 import pool

            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                raise Exception("DATABASE_URL environment variable not set")

            self.pg_pool = psycopg2.pool.SimpleConnectionPool(1, 20, database_url)
            self.init_postgres_database()
            logger.info("PostgreSQL database initialized")

        except ImportError:
            logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
            self.pg_pool = None
            self.use_postgres = False
            self.init_sqlite_database()
        except Exception as e:
            logger.error(f"Error setting up PostgreSQL: {e}")
            # Fall back to SQLite so the app still starts
            self.pg_pool = None
            self.use_postgres = False
            self.init_sqlite_database()

    def get_connection(self):
        """Get database connection (SQLite or PostgreSQL)"""
        if self.use_postgres:
            return self.pg_pool.getconn()
        else:
            return sqlite3.connect(self.db_path)

    def release_connection(self, conn):
        """Release database connection"""
        if self.use_postgres:
            self.pg_pool.putconn(conn)
        else:
            conn.close()

    def init_sqlite_database(self):
        """Initialize SQLite database with all tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                location TEXT,
                category TEXT NOT NULL,
                price TEXT,
                source TEXT,
                source_url TEXT,
                registration_deadline TEXT,
                is_user_added INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Bookmarks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                bookmarked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                notify_registration INTEGER DEFAULT 1,
                notify_day_before INTEGER DEFAULT 1,
                notify_3hours_before INTEGER DEFAULT 1,
                registration_reminded INTEGER DEFAULT 0,
                day_before_reminded INTEGER DEFAULT 0,
                three_hours_reminded INTEGER DEFAULT 0,
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
        ''')

        # Notification settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                daily_reminder_enabled INTEGER DEFAULT 1,
                daily_reminder_time TEXT DEFAULT '08:00',
                last_daily_notification TEXT,
                push_enabled INTEGER DEFAULT 0,
                push_subscription TEXT
            )
        ''')

        # Insert default notification settings if not exists
        cursor.execute('SELECT COUNT(*) FROM notification_settings')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO notification_settings (daily_reminder_enabled, daily_reminder_time)
                VALUES (1, '08:00')
            ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_start_date ON events(start_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_category ON events(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_event_id ON bookmarks(event_id)')

        conn.commit()
        conn.close()
        logger.info("SQLite database initialized")

    def init_postgres_database(self):
        """Initialize PostgreSQL database with all tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP,
                location TEXT,
                category TEXT NOT NULL,
                price TEXT,
                source TEXT,
                source_url TEXT,
                registration_deadline TIMESTAMP,
                is_user_added INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Bookmarks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL,
                bookmarked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notify_registration INTEGER DEFAULT 1,
                notify_day_before INTEGER DEFAULT 1,
                notify_3hours_before INTEGER DEFAULT 1,
                registration_reminded INTEGER DEFAULT 0,
                day_before_reminded INTEGER DEFAULT 0,
                three_hours_reminded INTEGER DEFAULT 0,
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
        ''')

        # Notification settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_settings (
                id SERIAL PRIMARY KEY,
                daily_reminder_enabled INTEGER DEFAULT 1,
                daily_reminder_time TEXT DEFAULT '08:00',
                last_daily_notification TIMESTAMP,
                push_enabled INTEGER DEFAULT 0,
                push_subscription TEXT
            )
        ''')

        conn.commit()
        self.release_connection(conn)

    # Event CRUD Operations
    def add_event(self, **kwargs) -> int:
        """Add a new event and return event_id"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if self.use_postgres:
                cursor.execute('''
                    INSERT INTO events (title, description, start_date, end_date, location,
                                      category, price, source, source_url, registration_deadline, is_user_added)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    kwargs.get('title'),
                    kwargs.get('description', ''),
                    kwargs.get('start_date'),
                    kwargs.get('end_date'),
                    kwargs.get('location'),
                    kwargs.get('category'),
                    kwargs.get('price'),
                    kwargs.get('source', 'User Added'),
                    kwargs.get('source_url'),
                    kwargs.get('registration_deadline'),
                    kwargs.get('is_user_added', 0)
                ))
                event_id = cursor.fetchone()[0]
            else:
                cursor.execute('''
                    INSERT INTO events (title, description, start_date, end_date, location,
                                      category, price, source, source_url, registration_deadline, is_user_added)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    kwargs.get('title'),
                    kwargs.get('description', ''),
                    kwargs.get('start_date'),
                    kwargs.get('end_date'),
                    kwargs.get('location'),
                    kwargs.get('category'),
                    kwargs.get('price'),
                    kwargs.get('source', 'User Added'),
                    kwargs.get('source_url'),
                    kwargs.get('registration_deadline'),
                    kwargs.get('is_user_added', 0)
                ))
                event_id = cursor.lastrowid

            conn.commit()
            logger.info(f"Added event: {kwargs.get('title')}")
            return event_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding event: {e}")
            raise
        finally:
            self.release_connection(conn)

    def add_events_batch(self, events: List[Dict]) -> int:
        """Add multiple events, skipping duplicates (same title + start_date). Returns count of newly added events."""
        added = 0
        for event in events:
            try:
                title = event.get('title', '')
                start_date = event.get('start_date', '')
                source_url = event.get('source_url', '')

                if not title or not start_date:
                    continue

                # Skip if duplicate (same source_url or same title+date)
                conn = self.get_connection()
                cursor = conn.cursor()
                placeholder = '%s' if self.use_postgres else '?'
                if source_url:
                    cursor.execute(
                        f'SELECT id FROM events WHERE source_url = {placeholder} LIMIT 1',
                        (source_url,)
                    )
                else:
                    cursor.execute(
                        f'SELECT id FROM events WHERE title = {placeholder} AND start_date = {placeholder} LIMIT 1',
                        (title, start_date)
                    )
                exists = cursor.fetchone()
                self.release_connection(conn)

                if exists:
                    continue

                self.add_event(
                    title=title,
                    description=event.get('description', ''),
                    start_date=start_date,
                    end_date=event.get('end_date'),
                    location=event.get('location', 'Philadelphia, PA'),
                    category=event.get('category', 'community'),
                    price=event.get('price'),
                    source=event.get('source', 'Unknown'),
                    source_url=source_url,
                    registration_deadline=event.get('registration_deadline'),
                    is_user_added=0
                )
                added += 1

            except Exception as e:
                logger.error(f"Error adding event in batch: {e}")
                continue

        return added

    def update_event(self, event_id: int, updates: Dict) -> bool:
        """Update an existing event"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Build dynamic update query
            fields = []
            values = []
            for key, value in updates.items():
                if key != 'id':
                    fields.append(f"{key} = ?" if not self.use_postgres else f"{key} = %s")
                    values.append(value)

            if not fields:
                return False

            # Add updated_at timestamp
            fields.append("updated_at = ?" if not self.use_postgres else "updated_at = CURRENT_TIMESTAMP")
            if not self.use_postgres:
                values.append(datetime.now().isoformat())

            values.append(event_id)

            query = f"UPDATE events SET {', '.join(fields)} WHERE id = {'?' if not self.use_postgres else '%s'}"
            cursor.execute(query, values)

            conn.commit()
            success = cursor.rowcount > 0
            logger.info(f"Updated event {event_id}: {success}")
            return success

        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating event: {e}")
            return False
        finally:
            self.release_connection(conn)

    def delete_event(self, event_id: int) -> bool:
        """Delete an event"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            placeholder = '?' if not self.use_postgres else '%s'
            cursor.execute(f'DELETE FROM events WHERE id = {placeholder}', (event_id,))
            conn.commit()
            success = cursor.rowcount > 0
            logger.info(f"Deleted event {event_id}: {success}")
            return success

        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting event: {e}")
            return False
        finally:
            self.release_connection(conn)

    def get_all_events(self) -> List[Dict]:
        """Get all events"""
        conn = self.get_connection()

        if self.use_postgres:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM events ORDER BY start_date ASC')
            columns = [desc[0] for desc in cursor.description]
            events = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM events ORDER BY start_date ASC')
            events = [dict(row) for row in cursor.fetchall()]

        self.release_connection(conn)
        return events

    def get_upcoming_events(self, limit: Optional[int] = None) -> List[Dict]:
        """Get upcoming events (from now onwards)"""
        conn = self.get_connection()
        now = datetime.now().isoformat()

        if self.use_postgres:
            cursor = conn.cursor()
            query = 'SELECT * FROM events WHERE start_date >= %s ORDER BY start_date ASC'
            if limit:
                query += f' LIMIT {limit}'
            cursor.execute(query, (now,))
            columns = [desc[0] for desc in cursor.description]
            events = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = 'SELECT * FROM events WHERE start_date >= ? ORDER BY start_date ASC'
            if limit:
                query += f' LIMIT {limit}'
            cursor.execute(query, (now,))
            events = [dict(row) for row in cursor.fetchall()]

        self.release_connection(conn)
        return events

    def get_events_by_category(self, category: str) -> List[Dict]:
        """Get events filtered by category"""
        conn = self.get_connection()
        placeholder = '%s' if self.use_postgres else '?'

        if self.use_postgres:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM events WHERE category = {placeholder} ORDER BY start_date ASC', (category,))
            columns = [desc[0] for desc in cursor.description]
            events = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM events WHERE category = {placeholder} ORDER BY start_date ASC', (category,))
            events = [dict(row) for row in cursor.fetchall()]

        self.release_connection(conn)
        return events

    def search_events(self, query: str) -> List[Dict]:
        """Search events by title or description"""
        conn = self.get_connection()
        search_term = f'%{query}%'

        if self.use_postgres:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM events
                WHERE title ILIKE %s OR description ILIKE %s
                ORDER BY start_date ASC
            ''', (search_term, search_term))
            columns = [desc[0] for desc in cursor.description]
            events = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM events
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY start_date ASC
            ''', (search_term, search_term))
            events = [dict(row) for row in cursor.fetchall()]

        self.release_connection(conn)
        return events

    # Bookmark Operations
    def add_bookmark(self, **kwargs) -> int:
        """Add event to bookmarks"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if self.use_postgres:
                cursor.execute('''
                    INSERT INTO bookmarks (event_id, notify_registration, notify_day_before, notify_3hours_before)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                ''', (
                    kwargs.get('event_id'),
                    kwargs.get('notify_registration', 1),
                    kwargs.get('notify_day_before', 1),
                    kwargs.get('notify_3hours_before', 1)
                ))
                bookmark_id = cursor.fetchone()[0]
            else:
                cursor.execute('''
                    INSERT INTO bookmarks (event_id, notify_registration, notify_day_before, notify_3hours_before)
                    VALUES (?, ?, ?, ?)
                ''', (
                    kwargs.get('event_id'),
                    kwargs.get('notify_registration', 1),
                    kwargs.get('notify_day_before', 1),
                    kwargs.get('notify_3hours_before', 1)
                ))
                bookmark_id = cursor.lastrowid

            conn.commit()
            return bookmark_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding bookmark: {e}")
            raise
        finally:
            self.release_connection(conn)

    def remove_bookmark(self, event_id: int) -> bool:
        """Remove event from bookmarks"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            placeholder = '%s' if self.use_postgres else '?'
            cursor.execute(f'DELETE FROM bookmarks WHERE event_id = {placeholder}', (event_id,))
            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Error removing bookmark: {e}")
            return False
        finally:
            self.release_connection(conn)

    def get_bookmarks(self) -> List[Dict]:
        """Get all bookmarked events with full event details"""
        conn = self.get_connection()

        if self.use_postgres:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.*, b.id as bookmark_id, b.bookmarked_at,
                       b.notify_registration, b.notify_day_before, b.notify_3hours_before
                FROM bookmarks b
                JOIN events e ON b.event_id = e.id
                ORDER BY e.start_date ASC
            ''')
            columns = [desc[0] for desc in cursor.description]
            bookmarks = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.*, b.id as bookmark_id, b.bookmarked_at,
                       b.notify_registration, b.notify_day_before, b.notify_3hours_before
                FROM bookmarks b
                JOIN events e ON b.event_id = e.id
                ORDER BY e.start_date ASC
            ''')
            bookmarks = [dict(row) for row in cursor.fetchall()]

        self.release_connection(conn)
        return bookmarks

    # Notification Settings
    def get_notification_settings(self) -> Dict:
        """Get notification settings"""
        conn = self.get_connection()

        if self.use_postgres:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM notification_settings LIMIT 1')
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                settings = dict(zip(columns, row))
            else:
                settings = {}
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM notification_settings LIMIT 1')
            row = cursor.fetchone()
            settings = dict(row) if row else {}

        self.release_connection(conn)
        return settings

    def update_notification_settings(self, updates: Dict) -> bool:
        """Update notification settings"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            fields = []
            values = []
            for key, value in updates.items():
                if key != 'id':
                    fields.append(f"{key} = ?" if not self.use_postgres else f"{key} = %s")
                    values.append(value)

            if not fields:
                return False

            query = f"UPDATE notification_settings SET {', '.join(fields)}"
            cursor.execute(query, values)

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating notification settings: {e}")
            return False
        finally:
            self.release_connection(conn)

    def get_stats(self) -> Dict:
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute('SELECT COUNT(*) FROM events')
        total = cursor.fetchone()[0]

        placeholder = '%s' if self.use_postgres else '?'
        cursor.execute(f'SELECT COUNT(*) FROM events WHERE start_date >= {placeholder}', (now,))
        upcoming = cursor.fetchone()[0]

        cursor.execute('SELECT category, COUNT(*) FROM events GROUP BY category')
        categories = dict(cursor.fetchall())

        cursor.execute('SELECT source, COUNT(*) FROM events GROUP BY source')
        sources = dict(cursor.fetchall())

        self.release_connection(conn)

        return {
            'total_events': total,
            'upcoming_events': upcoming,
            'by_category': categories,
            'by_source': sources
        }
