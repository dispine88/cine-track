"""Isolated tests for CineTrack's SQLite CRUD layer."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from database import db, crud, seed


class DatabaseCrudTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_cinetrack.db"
        self.path_patch = patch.object(db, "DB_PATH", self.db_path)
        self.path_patch.start()
        db.init_db()

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_title_crud_and_duplicate_path(self):
        self.assertTrue(crud.add_title("Arrival", file_path="/media/arrival.mkv"))
        self.assertFalse(crud.add_title("Duplicate", file_path="/media/arrival.mkv"))
        title = crud.get_all_titles()[0]
        self.assertEqual(title.name, "Arrival")
        self.assertTrue(crud.update_title_info(title.id, year=2016, status="watched"))
        self.assertEqual(crud.get_title(title.id).year, 2016)
        self.assertTrue(crud.delete_title(title.id))
        self.assertIsNone(crud.get_title(title.id))

    def test_bulk_scan_is_deduplicated(self):
        rows = [
            {"name": "A", "file_path": "/media/a.mkv"},
            {"name": "A duplicate", "file_path": "/media/a.mkv"},
            {"name": "B", "file_path": "/media/b.mkv"},
        ]
        self.assertEqual(crud.add_titles_bulk(rows), 2)
        self.assertEqual(crud.add_titles_bulk(rows), 0)

    def test_genre_association_and_reviews(self):
        crud.add_title("Dune", file_path="/media/dune.mkv")
        title = crud.get_all_titles()[0]
        genre_id = crud.add_genre("Sci-Fi")
        self.assertTrue(crud.add_title_genre(title.id, genre_id))
        self.assertFalse(crud.add_title_genre(title.id, genre_id))
        self.assertEqual(crud.get_title_genres(title.id)[0]["name"], "Sci-Fi")

        review_id = crud.add_review(title.id, 9, "Great")
        self.assertEqual(crud.get_reviews(title.id)[0]["rating"], 9)
        self.assertTrue(crud.update_review(review_id, rating=10, text="Excellent"))
        self.assertEqual(crud.get_reviews(title.id)[0]["rating"], 10)
        self.assertTrue(crud.update_review(review_id, rating=None))
        self.assertIsNone(crud.get_reviews(title.id)[0]["rating"])
        self.assertTrue(crud.delete_title(title.id))
        self.assertEqual(crud.get_reviews(title.id), [])

    def test_canonical_path_prevents_slash_and_dot_duplicates(self):
        import os
        first_path = os.path.join(self.temp_dir.name, "library", "movie.mkv")
        second_path = os.path.join(self.temp_dir.name, "library", ".", "movie.mkv")
        self.assertTrue(crud.add_title("Movie", file_path=first_path))
        self.assertFalse(crud.add_title("Movie duplicate", file_path=second_path))

    def test_merge_duplicate_paths_keeps_poster_reviews_and_genres(self):
        import os
        file_path = os.path.join(self.temp_dir.name, "movie.mkv")
        self.assertTrue(crud.add_title("Movie", file_path=file_path))
        keeper = crud.get_all_titles()[0]
        crud.update_title_info(keeper.id, year=2020, poster_url="https://image.tmdb.org/poster.jpg")

        duplicate_path = os.path.join(self.temp_dir.name, ".", "movie.mkv")
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO titles(name, type, status, file_path) VALUES (?, ?, ?, ?)",
                ("Movie duplicate", "local", "want", duplicate_path),
            )
            duplicate_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        genre_id = crud.add_genre("Drama")
        crud.add_title_genre(duplicate_id, genre_id)
        review_id = crud.add_review(duplicate_id, 8, "Good")

        merged = crud.merge_duplicate_file_paths()
        self.assertIn((duplicate_id, keeper.id), merged)
        self.assertEqual(len(crud.get_all_titles()), 1)
        self.assertEqual(crud.get_title(keeper.id).poster_url, "https://image.tmdb.org/poster.jpg")
        self.assertEqual(crud.get_title_genres(keeper.id)[0]["name"], "Drama")
        self.assertEqual(crud.get_reviews(keeper.id)[0]["id"], review_id)

    def test_foreign_keys_are_enabled(self):
        with db.get_connection() as conn:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_concurrent_add_title_does_not_create_duplicate_paths(self):
        path = str(Path(self.temp_dir.name) / "shared.mkv")
        def add(index):
            return crud.add_title(f"Copy {index}", file_path=path)

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(add, range(6)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(len(crud.get_all_titles()), 1)

    def test_nullable_title_fields_can_be_cleared(self):
        crud.add_title("Movie", file_path="/media/movie.mkv")
        title = crud.get_all_titles()[0]
        crud.update_title_info(
            title.id, year=2020, poster_url="https://image.tmdb.org/poster.jpg"
        )
        self.assertTrue(crud.update_title_info(title.id, year=None, poster_url=None))
        updated = crud.get_title(title.id)
        self.assertIsNone(updated.year)
        self.assertIsNone(updated.poster_url)

    def test_seed_fills_partial_database_and_is_idempotent(self):
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO titles(name, year, type, status) VALUES (?, ?, ?, ?)",
                ("Interstellar", 2014, "movie", "watched"),
            )
        self.assertEqual(seed.seed_data(), 2)
        self.assertEqual(seed.seed_data(), 0)
        self.assertEqual(len(crud.get_all_titles()), 3)

    def test_schema_version_is_recorded(self):
        with db.get_connection() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
        self.assertEqual(version, db.SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
