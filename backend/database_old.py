"""
Simple database module for storing scraped events
Uses SQLite for simplicity
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EventDatabase:
    """Simple SQLite database for events"""

    def __init__(self, db_path: str = "events.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database with events table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                location TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                source_url TEXT,
                image_url TEXT,
                price TEXT,
                is_manually_added INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title, start_date, source)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("Database initialized")

    def add_event(self, event: Dict) -> bool:
        """Add a single event to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO events
                (title, description, start_date, end_date, location, category,
                 source, source_url, image_url, price, is_manually_added)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event['title'],
                event['description'],
                event['start_date'],
                event.get('end_date'),
                event['location'],
                event['category'],
                event['source'],
                event.get('source_url'),
                event.get('image_url'),
                event.get('price'),
                event.get('is_manually_added', False)
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error adding event: {e}")
            return False

    def add_events_batch(self, events: List[Dict]) -> int:
        """Add multiple events to database"""
        added = 0
        for event in events:
            if self.add_event(event):
                added += 1
        return added

    def get_all_events(self) -> List[Dict]:
        """Get all events from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM events ORDER BY start_date ASC')
        rows = cursor.fetchall()

        events = [dict(row) for row in rows]
        conn.close()

        return events

    def get_upcoming_events(self, limit: Optional[int] = None) -> List[Dict]:
        """Get upcoming events (from now onwards)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        query = 'SELECT * FROM events WHERE start_date >= ? ORDER BY start_date ASC'

        if limit:
            query += f' LIMIT {limit}'

        cursor.execute(query, (now,))
        rows = cursor.fetchall()

        events = [dict(row) for row in rows]
        conn.close()

        return events

    def get_events_by_category(self, category: str) -> List[Dict]:
        """Get events filtered by category"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM events WHERE category = ? ORDER BY start_date ASC',
            (category,)
        )
        rows = cursor.fetchall()

        events = [dict(row) for row in rows]
        conn.close()

        return events

    def search_events(self, query: str) -> List[Dict]:
        """Search events by title or description"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        search_term = f'%{query}%'
        cursor.execute('''
            SELECT * FROM events
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY start_date ASC
        ''', (search_term, search_term))

        rows = cursor.fetchall()
        events = [dict(row) for row in rows]
        conn.close()

        return events

    def delete_old_events(self, days_old: int = 30):
        """Delete events older than specified days"""
        from datetime import timedelta

        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM events WHERE start_date < ?', (cutoff_date,))
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        logger.info(f"Deleted {deleted} old events")
        return deleted

    def get_stats(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM events')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM events WHERE start_date >= ?',
                      (datetime.now().isoformat(),))
        upcoming = cursor.fetchone()[0]

        cursor.execute('SELECT category, COUNT(*) FROM events GROUP BY category')
        categories = dict(cursor.fetchall())

        cursor.execute('SELECT source, COUNT(*) FROM events GROUP BY source')
        sources = dict(cursor.fetchall())

        conn.close()

        return {
            'total_events': total,
            'upcoming_events': upcoming,
            'by_category': categories,
            'by_source': sources
        }
