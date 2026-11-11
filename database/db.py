import os
import sqlite3
from config import APP_DIR

DB_PATH = os.path.join(APP_DIR, "cinetrack.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                year INTEGER,
                type TEXT,
                status TEXT,
                file_path TEXT,
                poster_url TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS title_genres (
                title_id INTEGER,
                genre_id INTEGER,
                FOREIGN KEY (title_id) REFERENCES titles(id),
                FOREIGN KEY (genre_id) REFERENCES genres(id),
                PRIMARY KEY (title_id, genre_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_id INTEGER,
                rating INTEGER,
                text TEXT,
                FOREIGN KEY (title_id) REFERENCES titles(id)
            )
        ''')
        conn.commit()