"""Tests for pure worker logic with a minimal Qt import stub when PyQt is absent."""
import csv
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    import PyQt5.QtCore  # noqa: F401
except ModuleNotFoundError:
    pyqt5 = types.ModuleType("PyQt5")
    qtcore = types.ModuleType("PyQt5.QtCore")

    class _Signal:
        def emit(self, *_args, **_kwargs):
            pass
        def connect(self, *_args, **_kwargs):
            pass

    class _QObject:
        def __init__(self, *_args, **_kwargs):
            pass

    class _QRunnable:
        def setAutoDelete(self, *_args, **_kwargs):
            pass

    qtcore.QObject = _QObject
    qtcore.QRunnable = _QRunnable
    qtcore.pyqtSignal = lambda *_args, **_kwargs: _Signal()
    qtcore.pyqtSlot = lambda *_args, **_kwargs: (lambda function: function)
    pyqt5.QtCore = qtcore
    sys.modules.setdefault("PyQt5", pyqt5)
    sys.modules.setdefault("PyQt5.QtCore", qtcore)

from gui import workers


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self.payload


class WorkerTests(unittest.TestCase):
    def test_clean_filename_removes_release_tags_and_normalizes_separators(self):
        self.assertEqual(
            workers.clean_filename("My.Show_Name[1080p](2020).mkv"),
            "My Show Name",
        )

    def test_tmdb_search_filters_people_and_limits_results(self):
        payload = {"results": [
            {"media_type": "person", "name": "Someone"},
            {"media_type": "movie", "title": "Arrival"},
            {"media_type": "tv", "name": "Dark"},
            {"media_type": "bad"},
            None,
        ]}
        with patch.object(workers.requests, "get", return_value=FakeResponse(payload)) as get:
            result = workers.search_tmdb_task("test", "key")
        self.assertEqual([item["media_type"] for item in result], ["movie", "tv"])
        self.assertEqual(get.call_args.kwargs["timeout"], (4, 12))

    def test_search_rejects_unexpected_tmdb_payload(self):
        with patch.object(workers.requests, "get", return_value=FakeResponse([1, 2, 3])):
            with self.assertRaises(RuntimeError):
                workers.search_tmdb_task("test", "key")

    def test_poster_metadata_update_does_not_clear_existing_poster(self):
        title_ids = [4]
        with patch.object(workers.crud, "update_title_info", return_value=True) as update:
            result = workers.download_posters_task(
                {"release_date": "2019-05-01", "poster_path": None}, title_ids
            )
        self.assertEqual(result, {"updated": 1, "poster_saved": False})
        update.assert_called_once_with(4, year=2019)

    def test_csv_export_writes_utf8_bom_and_rows(self):
        title = SimpleNamespace(
            name="Ёжик в тумане", year=1975, type="movie",
            status="watched", file_path="C:/media/movie.mkv",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "library.csv"
            with patch.object(workers.crud, "get_all_titles", return_value=[title]):
                count = workers.export_csv_task(str(target))
            self.assertEqual(count, 1)
            raw = target.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            with target.open("r", encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.reader(stream))
            self.assertEqual(rows[1][0], "Ёжик в тумане")

    def test_invalid_poster_path_is_rejected_before_network_call(self):
        with patch.object(workers.requests, "get") as get:
            with self.assertRaises(RuntimeError):
                workers.download_posters_task({"poster_path": "/../outside.jpg"}, [1])
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
