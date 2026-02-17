"""
Create a fresh database with improved schema
Includes: events, bookmarks, notification settings, and user preferences
"""

import sqlite3
from datetime import datetime

def create_fresh_database():
    # Backup old database
    import shutil
    import os

    if os.path.exists('events.db'):
        backup_name = f'events_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy('events.db', backup_name)
        print(f"✅ Backed up old database to: {backup_name}")
        os.remove('events.db')
        print("✅ Removed old database")

    # Create new database
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()

    # Events table - main event data
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

    # Bookmarks table - user's saved events
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

    # Insert default notification settings
    cursor.execute('''
        INSERT INTO notification_settings (daily_reminder_enabled, daily_reminder_time)
        VALUES (1, '08:00')
    ''')

    # Create indexes for performance
    cursor.execute('CREATE INDEX idx_events_start_date ON events(start_date)')
    cursor.execute('CREATE INDEX idx_events_category ON events(category)')
    cursor.execute('CREATE INDEX idx_bookmarks_event_id ON bookmarks(event_id)')

    conn.commit()
    conn.close()

    print("\n✅ Created fresh database with schema:")
    print("   - events: Main event storage")
    print("   - bookmarks: User's saved events with notification preferences")
    print("   - notification_settings: Global notification preferences")
    print("\n📊 Database is ready at: events.db")
    print("🎯 Next step: Start adding events manually through the UI")

if __name__ == "__main__":
    create_fresh_database()
