# ================= DATABASE SETUP =================
# Add to your database.py or models.py file

import sqlite3
import json
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('nomadx.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_user_profile_table():
    """Create user profile table if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            name TEXT NOT NULL DEFAULT 'John Doe',
            email TEXT NOT NULL,
            photo BLOB,
            google_linked INTEGER DEFAULT 0,
            google_name TEXT,
            google_email TEXT,
            google_photo TEXT,
            theme TEXT DEFAULT 'dark',
            language TEXT DEFAULT 'en',
            notifications INTEGER DEFAULT 1,
            email_prefs INTEGER DEFAULT 1,
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default profile if not exists
    cursor.execute('''
        INSERT OR IGNORE INTO user_profiles (user_id, name, email, google_linked)
        VALUES (1, 'John Doe', 'john.doe@email.com', 0)
    ''')
    
    conn.commit()
    conn.close()

# Call this function when your app starts
# init_user_profile_table()