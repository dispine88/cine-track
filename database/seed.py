"""Idempotent sample data for manual development and demonstrations."""
from database.db import get_connection, init_db


SAMPLE_TITLES = (
    ("Interstellar", 2014, "movie", "watched"),
    ("Breaking Bad", 2008, "series", "watched"),
    ("John Wick", 2014, "movie", "want"),
)


def seed_data() -> int:
    """Insert missing sample titles without duplicating a partially seeded DB."""
    init_db()
    added = 0
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for name, year, media_type, status in SAMPLE_TITLES:
            exists = conn.execute(
                "SELECT 1 FROM titles WHERE name = ? COLLATE NOCASE AND year = ? AND type = ? LIMIT 1",
                (name, year, media_type),
            ).fetchone()
            if exists is None:
                conn.execute(
                    "INSERT INTO titles (name, year, type, status) VALUES (?, ?, ?, ?)",
                    (name, year, media_type, status),
                )
                added += 1
    return added


if __name__ == "__main__":
    count = seed_data()
    print(f"Inserted {count} sample title(s)." if count else "Sample data already present.")
