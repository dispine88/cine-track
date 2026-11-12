"""Parameterized CRUD operations for CineTrack's SQLite database."""
from dataclasses import dataclass
import os
from typing import Optional, Iterable

from database.db import get_connection


@dataclass
class Title:
    id: int
    name: str
    year: Optional[int]
    type: Optional[str]
    status: Optional[str]
    file_path: Optional[str]
    poster_url: Optional[str]


def normalize_file_path(file_path):
    """Return a stable identity for a local file path across case/slash variants."""
    if not file_path:
        return None
    expanded = os.path.expanduser(os.fspath(file_path))
    return os.path.normcase(os.path.realpath(os.path.abspath(expanded)))

def get_all_titles():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM titles ORDER BY name COLLATE NOCASE").fetchall()
        return [Title(**dict(row)) for row in rows]


def get_title(title_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM titles WHERE id = ?", (title_id,)).fetchone()
        return Title(**dict(row)) if row else None


def add_title(name, type="manual", status="want", file_path=None):
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Title name cannot be empty")
    with get_connection() as conn:
        if file_path:
            candidate_key = normalize_file_path(file_path)
            existing_paths = conn.execute(
                "SELECT file_path FROM titles WHERE file_path IS NOT NULL"
            ).fetchall()
            if any(normalize_file_path(row[0]) == candidate_key for row in existing_paths):
                return False
        conn.execute(
            "INSERT INTO titles (name, type, status, file_path) VALUES (?, ?, ?, ?)",
            (clean_name, type, status, file_path),
        )
        return True


def add_titles_bulk(records: Iterable[dict]) -> int:
    """Insert scanned files in one transaction; return number of new rows."""
    prepared = []
    for record in records:
        name = str(record.get("name", "")).strip()
        path = record.get("file_path")
        if name and path:
            prepared.append((name, record.get("type", "local"),
                             record.get("status", "want"), str(path)))
    if not prepared:
        return 0

    added = 0
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT file_path FROM titles WHERE file_path IS NOT NULL"
        ).fetchall()
        seen = {normalize_file_path(row[0]) for row in existing}
        unique_rows = []
        for row in prepared:
            path_key = normalize_file_path(row[3])
            if path_key not in seen:
                seen.add(path_key)
                unique_rows.append(row)
        conn.executemany(
            "INSERT INTO titles (name, type, status, file_path) VALUES (?, ?, ?, ?)",
            unique_rows,
        )
        added = len(unique_rows)
    return added


def merge_duplicate_file_paths():
    """Merge rows that refer to the same canonical file path.

    The record with the richest metadata (especially a TMDB poster) survives.
    Reviews and genre associations are moved to it before duplicate rows are removed.
    Returns ``[(removed_id, kept_id), ...]`` for poster-cache migration by the caller.
    """
    merged = []
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, year, type, status, file_path, poster_url "
            "FROM titles WHERE file_path IS NOT NULL ORDER BY id"
        ).fetchall()
        groups = {}
        for row in rows:
            key = normalize_file_path(row["file_path"])
            if key:
                groups.setdefault(key, []).append(dict(row))

        for group in groups.values():
            if len(group) < 2:
                continue

            # Keep the entry that already has a poster/metadata so its cache ID survives.
            group.sort(key=lambda item: (
                bool(item.get("poster_url")),
                item.get("year") is not None,
                bool(item.get("type") and item.get("type") != "local"),
                -int(item["id"]),
            ), reverse=True)
            keeper = group[0]
            keeper_id = int(keeper["id"])

            for duplicate in group[1:]:
                duplicate_id = int(duplicate["id"])
                updates = {}
                for field in ("year", "poster_url"):
                    if not keeper.get(field) and duplicate.get(field):
                        updates[field] = duplicate[field]
                if keeper.get("type") in (None, "", "local") and duplicate.get("type") not in (None, "", "local"):
                    updates["type"] = duplicate["type"]
                if keeper.get("status") in (None, "") and duplicate.get("status"):
                    updates["status"] = duplicate["status"]
                if updates:
                    assignments = ", ".join(f"{column} = ?" for column in updates)
                    conn.execute(
                        f"UPDATE titles SET {assignments} WHERE id = ?",
                        [*updates.values(), keeper_id],
                    )
                    keeper.update(updates)

                conn.execute(
                    "INSERT OR IGNORE INTO title_genres(title_id, genre_id) "
                    "SELECT ?, genre_id FROM title_genres WHERE title_id = ?",
                    (keeper_id, duplicate_id),
                )
                conn.execute("DELETE FROM title_genres WHERE title_id = ?", (duplicate_id,))
                conn.execute("UPDATE reviews SET title_id = ? WHERE title_id = ?", (keeper_id, duplicate_id))
                conn.execute("DELETE FROM titles WHERE id = ?", (duplicate_id,))
                merged.append((duplicate_id, keeper_id))

    return merged


def delete_title(title_id):
    """Delete metadata and dependent rows, never touch the source video file."""
    with get_connection() as conn:
        conn.execute("DELETE FROM title_genres WHERE title_id = ?", (title_id,))
        conn.execute("DELETE FROM reviews WHERE title_id = ?", (title_id,))
        cursor = conn.execute("DELETE FROM titles WHERE id = ?", (title_id,))
        return cursor.rowcount > 0


def delete_titles(title_ids):
    deleted = 0
    with get_connection() as conn:
        for title_id in set(title_ids):
            conn.execute("DELETE FROM title_genres WHERE title_id = ?", (title_id,))
            conn.execute("DELETE FROM reviews WHERE title_id = ?", (title_id,))
            deleted += conn.execute("DELETE FROM titles WHERE id = ?", (title_id,)).rowcount
    return deleted


def update_title_info(title_id, year=None, poster_url=None, name=None,
                      title_type=None, status=None):
    fields = {
        "year": year,
        "poster_url": poster_url,
        "name": name.strip() if isinstance(name, str) else name,
        "type": title_type,
        "status": status,
    }
    updates = [(column, value) for column, value in fields.items() if value is not None]
    if not updates:
        return False
    sql = ", ".join(f"{column} = ?" for column, _ in updates)
    values = [value for _, value in updates] + [title_id]
    with get_connection() as conn:
        cursor = conn.execute(f"UPDATE titles SET {sql} WHERE id = ?", values)
        return cursor.rowcount > 0


# Genres and the many-to-many association.
def add_genre(name):
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Genre name cannot be empty")
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO genres(name) VALUES (?)", (clean_name,))
        row = conn.execute("SELECT id FROM genres WHERE name = ?", (clean_name,)).fetchone()
        return row[0]


def get_all_genres():
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM genres ORDER BY name COLLATE NOCASE")]


def update_genre(genre_id, name):
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Genre name cannot be empty")
    with get_connection() as conn:
        cursor = conn.execute("UPDATE genres SET name = ? WHERE id = ?", (clean_name, genre_id))
        return cursor.rowcount > 0


def delete_genre(genre_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM title_genres WHERE genre_id = ?", (genre_id,))
        cursor = conn.execute("DELETE FROM genres WHERE id = ?", (genre_id,))
        return cursor.rowcount > 0


def add_title_genre(title_id, genre_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO title_genres(title_id, genre_id) VALUES (?, ?)",
            (title_id, genre_id),
        )
        return cursor.rowcount > 0


def remove_title_genre(title_id, genre_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM title_genres WHERE title_id = ? AND genre_id = ?",
            (title_id, genre_id),
        )
        return cursor.rowcount > 0


def get_title_genres(title_id):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT g.id, g.name FROM genres g
               JOIN title_genres tg ON tg.genre_id = g.id
               WHERE tg.title_id = ? ORDER BY g.name COLLATE NOCASE""",
            (title_id,),
        ).fetchall()
        return [dict(row) for row in rows]


# Reviews.
def add_review(title_id, rating=None, text=""):
    if rating is not None and not 1 <= int(rating) <= 10:
        raise ValueError("Rating must be between 1 and 10")
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO reviews(title_id, rating, text) VALUES (?, ?, ?)",
            (title_id, rating, (text or "").strip()),
        )
        return cursor.lastrowid


def get_reviews(title_id=None):
    with get_connection() as conn:
        if title_id is None:
            rows = conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM reviews WHERE title_id = ? ORDER BY id DESC", (title_id,)
            ).fetchall()
        return [dict(row) for row in rows]


def update_review(review_id, rating=None, text=None):
    if rating is not None and not 1 <= int(rating) <= 10:
        raise ValueError("Rating must be between 1 and 10")
    updates = []
    if rating is not None:
        updates.append(("rating", int(rating)))
    if text is not None:
        updates.append(("text", text.strip()))
    if not updates:
        return False
    assignments = ", ".join(f"{column} = ?" for column, _ in updates)
    values = [value for _, value in updates] + [review_id]
    with get_connection() as conn:
        cursor = conn.execute(f"UPDATE reviews SET {assignments} WHERE id = ?", values)
        return cursor.rowcount > 0


def delete_review(review_id):
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        return cursor.rowcount > 0
