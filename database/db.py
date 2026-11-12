"""SQLite connection management and schema initialization."""
import sqlite3
from contextlib import contextmanager

from config import DB_PATH


SCHEMA_VERSION = 1


@contextmanager
def get_connection():
    """Yield a configured connection and always commit/rollback and close it."""
    conn = sqlite3.connect(str(DB_PATH), timeout=8.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 8000")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create the current schema and mark the initial schema version.

    Future structural changes should be added as explicit migrations keyed by
    PRAGMA user_version rather than relying on CREATE TABLE IF NOT EXISTS.
    """
    with get_connection() as conn:
        current_version = conn.execute("PRAGMA user_version").fetchone()[0]
        if current_version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {current_version} is newer than this app supports"
            )
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                year INTEGER,
                type TEXT,
                status TEXT,
                file_path TEXT,
                poster_url TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS title_genres (
                title_id INTEGER NOT NULL,
                genre_id INTEGER NOT NULL,
                PRIMARY KEY (title_id, genre_id),
                FOREIGN KEY (title_id) REFERENCES titles(id) ON DELETE CASCADE,
                FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_id INTEGER NOT NULL,
                rating INTEGER,
                text TEXT,
                FOREIGN KEY (title_id) REFERENCES titles(id) ON DELETE CASCADE
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_titles_name ON titles(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_title_id ON reviews(title_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_title_genres_genre_id ON title_genres(genre_id)")
        if current_version < SCHEMA_VERSION:
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
