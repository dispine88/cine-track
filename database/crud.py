from dataclasses import dataclass
from typing import Optional
from database.db import get_connection

@dataclass
class Title:
    id: int
    name: str
    year: Optional[int]
    type: str
    status: str
    file_path: Optional[str]
    poster_url: Optional[str]

def get_all_titles():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM titles ORDER BY name")
        rows = cursor.fetchall()
        return [Title(**dict(row)) for row in rows]

def get_title(title_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM titles WHERE id = ?", (title_id,))
        row = cursor.fetchone()
        return Title(**dict(row)) if row else None

def add_title(name, type="manual", status="want", file_path=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if file_path:
            cursor.execute("SELECT id FROM titles WHERE file_path = ?", (file_path,))
            if cursor.fetchone():
                return False
        cursor.execute(
            "INSERT INTO titles (name, type, status, file_path) VALUES (?, ?, ?, ?)",
            (name, type, status, file_path)
        )
        conn.commit()
        return True

def delete_title(title_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM titles WHERE id = ?", (title_id,))
        conn.commit()
        return True

def update_title_info(title_id, year=None, poster_url=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if year is not None and poster_url is not None:
            cursor.execute("UPDATE titles SET year = ?, poster_url = ? WHERE id = ?", (year, poster_url, title_id))
        elif year is not None:
            cursor.execute("UPDATE titles SET year = ? WHERE id = ?", (year, title_id))
        elif poster_url is not None:
            cursor.execute("UPDATE titles SET poster_url = ? WHERE id = ?", (poster_url, title_id))
        conn.commit()
        return True