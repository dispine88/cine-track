"""Main CineTrack window."""
import csv
import os
import subprocess
import sys
from html import escape
from pathlib import Path

from PyQt5.QtCore import Qt, QThreadPool, pyqtSlot, QSize
from PyQt5.QtGui import QPixmap, QImageReader
from PyQt5.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QPushButton, QSplitter, QVBoxLayout,
    QWidget, QDialog,
)

import config
from database import crud
from gui.constants import TRANSLATIONS
from gui.dialogs import (
    CustomInputDialog, CustomMessageBox, CustomTitleBar, SearchDialog,
)
from gui.settings_dialog import SettingsDialog
from gui.workers import (
    FunctionWorker, download_posters_task, export_csv_task, qbittorrent_task, scan_folder_task,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CineTrack - Local Media")
        self.resize(1100, 750)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.settings = config.load_settings()
        self.lang = self.settings.get("language", "RU")
        if self.lang not in TRANSLATIONS:
            self.lang = "RU"
        self._workers = {}
        self._scan_busy = False
        self._poster_busy = False
        self._qbit_busy = False
        self._export_busy = False
        self._selected_ids_after_search = []
        self._active_message = None

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.title_bar = CustomTitleBar(self, "CineTrack - Local Media")
        main_layout.addWidget(self.title_bar)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(content_widget)

        top_layout = QHBoxLayout()
        self.scan_btn = QPushButton()
        self.scan_btn.clicked.connect(self.scan_folder)
        self.add_btn = QPushButton()
        self.add_btn.clicked.connect(self.add_manual)
        self.search_btn = QPushButton()
        self.search_btn.clicked.connect(self.open_search_dialog)
        self.qbit_btn = QPushButton()
        self.qbit_btn.clicked.connect(self.check_qbittorrent)
        self.export_btn = QPushButton()
        self.export_btn.clicked.connect(self.export_to_csv)
        self.settings_btn = QPushButton()
        self.settings_btn.clicked.connect(self.open_settings)
        self.lang_btn = QPushButton()
        self.lang_btn.setFixedWidth(50)
        self.lang_btn.clicked.connect(self.toggle_language)
        for button in (self.scan_btn, self.add_btn, self.search_btn,
                       self.qbit_btn, self.export_btn, self.settings_btn, self.lang_btn):
            top_layout.addWidget(button)
        content_layout.addLayout(top_layout)

        splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(splitter)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self.on_item_selected)
        self.list_widget.itemDoubleClicked.connect(self.play_video)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.list_widget)
        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setMinimumHeight(400)
        self.poster_label.setMaximumWidth(460)
        self.details_label = QLabel()
        self.details_label.setAlignment(Qt.AlignTop)
        self.details_label.setWordWrap(True)
        self.play_btn = QPushButton()
        self.play_btn.clicked.connect(self.play_video)
        self.play_btn.setEnabled(False)
        right_layout.addWidget(self.poster_label)
        right_layout.addWidget(self.details_label)
        right_layout.addWidget(self.play_btn)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 450])

        self.statusBar().showMessage("Ready")
        self.update_ui_text()
        self.load_data()

    def _start_worker(self, function, on_result, on_error):
        worker = FunctionWorker(function)
        self._workers[worker.job_id] = worker
        worker.signals.result.connect(on_result)
        worker.signals.error.connect(on_error)
        worker.signals.finished.connect(self._on_worker_finished)
        QThreadPool.globalInstance().start(worker)

    @pyqtSlot(object)
    def _on_worker_finished(self, job_id):
        self._workers.pop(job_id, None)

    def update_ui_text(self):
        text = TRANSLATIONS[self.lang]
        self.scan_btn.setText(text["scan"])
        self.add_btn.setText(text["add"])
        self.search_btn.setText(text["search"])
        self.play_btn.setText(text["play"])
        self.qbit_btn.setText(text["qbit"])
        self.export_btn.setText(text["export"])
        self.settings_btn.setText("⚙ Настройки" if self.lang == "RU" else "⚙ Settings")
        self.poster_label.setText(text["no_poster"])
        self.details_label.setText(f"<h2>{escape(text['select_file'])}</h2>")
        self.lang_btn.setText("EN" if self.lang == "RU" else "RU")

    def open_settings(self):
        """Open the compact settings editor and persist secrets through Keyring."""
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec_() != QDialog.Accepted:
            return

        data = dialog.settings_data.copy()
        secret_names = ("tmdb_api_key", "qbit_pass")
        old_secrets = {name: config.get_secret(name) for name in secret_names}
        try:
            config.set_secret("tmdb_api_key", dialog.tmdb_api_key)
            config.set_secret("qbit_pass", dialog.qbit_password)
            config.save_settings(data)
        except Exception as exc:
            # Restore both credentials if one write or the settings file failed.
            for name, old_value in old_secrets.items():
                try:
                    config.set_secret(name, old_value)
                except Exception:
                    pass
            self.show_message(
                "error",
                ("Не удалось сохранить настройки. Проверьте системное хранилище паролей. "
                 if self.lang == "RU" else
                 "Could not save settings. Check the system credential manager. ")
                + f"({type(exc).__name__})",
            )
            return

        config.reload_secrets()
        self.settings = data
        self.statusBar().showMessage(
            "Настройки сохранены" if self.lang == "RU" else "Settings saved", 5000
        )

    def toggle_language(self):
        self.lang = "EN" if self.lang == "RU" else "RU"
        self.settings["language"] = self.lang
        try:
            config.save_settings(self.settings)
        except OSError:
            self.show_message("error", "Не удалось сохранить настройки" if self.lang == "RU" else "Could not save settings")
        self.update_ui_text()
        self.load_data()

    def clean_filename(self, filename):
        from gui.workers import clean_filename
        return clean_filename(filename)

    def scan_folder(self):
        if self._scan_busy:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку" if self.lang == "RU" else "Select folder"
        )
        if not folder:
            return
        self._scan_busy = True
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Сканирование…" if self.lang == "RU" else "Scanning…")
        self.statusBar().showMessage("Сканирование медиатеки…" if self.lang == "RU" else "Scanning media library…")
        self._start_worker(lambda: scan_folder_task(folder), self._on_scan_finished, self._on_scan_error)

    def _restore_scan_button(self):
        self._scan_busy = False
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText(TRANSLATIONS[self.lang]["scan"])

    def _on_scan_finished(self, result):
        self._restore_scan_button()
        self.load_data()
        if self.lang == "RU":
            message = f"Найдено видео: {result['found']}. Добавлено новых записей: {result['added']}."
            if result.get("merged_duplicates"):
                message += f" Объединено дублей: {result['merged_duplicates']}."
            if result["walk_errors"]:
                message += f" Не удалось прочитать каталогов: {result['walk_errors']}."
        else:
            message = f"Videos found: {result['found']}. New entries: {result['added']}."
            if result.get("merged_duplicates"):
                message += f" Merged duplicates: {result['merged_duplicates']}."
            if result["walk_errors"]:
                message += f" Unreadable directories: {result['walk_errors']}."
        self.statusBar().showMessage(message, 10000)

    def _on_scan_error(self, _error):
        self._restore_scan_button()
        self.show_message("error", "Не удалось просканировать папку." if self.lang == "RU" else "The folder could not be scanned.")

    def add_manual(self):
        dialog = CustomInputDialog(
            self,
            "Добавить" if self.lang == "RU" else "Add",
            "Введите название:" if self.lang == "RU" else "Enter title:",
        )
        if dialog.exec_() == QDialog.Accepted:
            text = dialog.get_text().strip()
            if text:
                crud.add_title(name=text, type="manual", status="want")
                self.load_data()

    def delete_item(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        title_ids = [item.data(Qt.UserRole) for item in selected_items]
        message = (
            f"Удалить {len(title_ids)} записей из медиатеки? Исходные видеофайлы останутся на диске."
            if self.lang == "RU" else
            f"Remove {len(title_ids)} entries from the library? Original video files will remain on disk."
        )
        dialog = CustomMessageBox(self, TRANSLATIONS[self.lang]["delete"], message)
        if dialog.exec_() == QDialog.Accepted:
            crud.delete_titles(title_ids)
            for title_id in title_ids:
                cache_path = Path(config.CACHE_DIR) / f"{int(title_id)}.jpg"
                try:
                    cache_path.unlink(missing_ok=True)
                except OSError:
                    pass
            self.load_data()

    def load_data(self):
        self.list_widget.clear()
        try:
            titles = crud.get_all_titles()
        except Exception:
            self.show_message("error", "Не удалось загрузить медиатеку" if self.lang == "RU" else "Could not load the media library")
            return
        for title in titles:
            year_text = f" ({title.year})" if title.year else ""
            display_text = f"{title.name}{year_text} [{title.type or 'local'}]"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, title.id)
            item.setToolTip(title.file_path or title.name)
            self.list_widget.addItem(item)

    def on_item_selected(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            self.play_btn.setEnabled(False)
            self.poster_label.setPixmap(QPixmap())
            self.poster_label.setText(TRANSLATIONS[self.lang]["no_poster"])
            self.details_label.setText(f"<h2>{escape(TRANSLATIONS[self.lang]['select_file'])}</h2>")
            return

        title = crud.get_title(selected_items[0].data(Qt.UserRole))
        if not title:
            self.play_btn.setEnabled(False)
            return
        self.play_btn.setEnabled(bool(title.file_path))
        safe_name = escape(title.name)
        safe_type = escape(title.type or "")
        year_label = str(title.year) if title.year else "?"
        text = TRANSLATIONS[self.lang]
        self.details_label.setText(
            f"<h3>{safe_name}</h3><p><b>{escape(text['details_type'])}:</b> {safe_type} | "
            f"<b>{escape(text['details_year'])}:</b> {year_label}</p>"
        )

        local_poster = self.find_local_poster(title.file_path)
        cached_poster = Path(config.CACHE_DIR) / f"{title.id}.jpg"
        image_path = local_poster or (str(cached_poster) if cached_poster.is_file() else None)
        if image_path:
            self.load_local_image(image_path)
        else:
            self.poster_label.setPixmap(QPixmap())
            self.poster_label.setText(TRANSLATIONS[self.lang]["no_poster"])

    @staticmethod
    def find_local_poster(file_path):
        if not file_path:
            return None
        folder = os.path.dirname(file_path)
        for name in ("poster.jpg", "cover.jpg", "folder.jpg", "poster.png", "cover.png"):
            candidate = os.path.join(folder, name)
            if os.path.isfile(candidate):
                return candidate
        return None

    def load_local_image(self, path):
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        original_size = reader.size()
        if original_size.isValid():
            reader.setScaledSize(original_size.scaled(QSize(400, 600), Qt.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            self.poster_label.setPixmap(QPixmap())
            self.poster_label.setText(TRANSLATIONS[self.lang]["no_poster"])
            if str(config.CACHE_DIR) in str(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            return
        self.poster_label.setPixmap(QPixmap.fromImage(image))

    def open_search_dialog(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            self.show_message("warning", TRANSLATIONS[self.lang]["select_file_warn"])
            return
        if self._poster_busy:
            return

        dialog = SearchDialog(self, self.lang)
        if dialog.exec_() != QDialog.Accepted or not dialog.selected_result:
            return

        self._selected_ids_after_search = [item.data(Qt.UserRole) for item in selected_items]
        self._poster_busy = True
        self.search_btn.setEnabled(False)
        self.statusBar().showMessage("Загрузка постера…" if self.lang == "RU" else "Downloading poster…")
        self._start_worker(
            lambda: download_posters_task(dialog.selected_result, self._selected_ids_after_search),
            self._on_posters_finished,
            self._on_posters_error,
        )

    def _on_posters_finished(self, result):
        self._poster_busy = False
        self.search_btn.setEnabled(True)
        self.load_data()
        if self._selected_ids_after_search:
            target_id = self._selected_ids_after_search[0]
            for index in range(self.list_widget.count()):
                item = self.list_widget.item(index)
                if item.data(Qt.UserRole) == target_id:
                    item.setSelected(True)
                    self.list_widget.setCurrentItem(item)
                    break
        self.on_item_selected()
        message = (
            f"Обновлено записей: {result['updated']}" if self.lang == "RU" else
            f"Entries updated: {result['updated']}"
        )
        self.statusBar().showMessage(message, 8000)

    def _on_posters_error(self, _error):
        self._poster_busy = False
        self.search_btn.setEnabled(True)
        self.show_message("error", "Не удалось загрузить данные TMDB. Проверьте подключение и попробуйте снова." if self.lang == "RU" else "TMDB data could not be downloaded. Check the connection and try again.")

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        if not item.isSelected():
            self.list_widget.clearSelection()
            item.setSelected(True)
        menu = QMenu(self)
        menu.addAction(TRANSLATIONS[self.lang]["play_ctx"], self.play_video)
        menu.addSeparator()
        menu.addAction(TRANSLATIONS[self.lang]["delete"], self.delete_item)
        menu.exec_(self.list_widget.viewport().mapToGlobal(pos))

    def play_video(self, *_args):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        title = crud.get_title(selected_items[0].data(Qt.UserRole))
        if not title or not title.file_path:
            return
        safe_path = os.path.abspath(title.file_path)
        if not os.path.isfile(safe_path):
            self.show_message("error", TRANSLATIONS[self.lang]["file_not_found"])
            return
        if not safe_path.lower().endswith((".mkv", ".mp4", ".avi", ".webm")):
            self.show_message("error", TRANSLATIONS[self.lang]["invalid_format"])
            return

        try:
            if sys.platform == "win32":
                os.startfile(safe_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", safe_path])
            else:
                try:
                    subprocess.Popen(["mpv", "--fs", safe_path])
                except FileNotFoundError:
                    subprocess.Popen(["xdg-open", safe_path])
        except (OSError, FileNotFoundError):
            self.show_message("error", "Не удалось открыть видео. Проверьте установленный видеоплеер." if self.lang == "RU" else "Could not open the video. Check your media player installation.")

    def export_to_csv(self):
        if self._export_busy:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV" if self.lang == "EN" else "Сохранить CSV", "CineTrack_library.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"
        self._export_busy = True
        self.export_btn.setEnabled(False)
        self.statusBar().showMessage("Экспорт CSV…" if self.lang == "RU" else "Exporting CSV…")
        self._start_worker(
            lambda: export_csv_task(file_path),
            self._on_export_finished,
            self._on_export_error,
        )

    def _on_export_finished(self, row_count):
        self._export_busy = False
        self.export_btn.setEnabled(True)
        message = (
            f"Экспортировано записей: {row_count}" if self.lang == "RU"
            else f"Exported entries: {row_count}"
        )
        self.statusBar().showMessage(message, 10000)

    def _on_export_error(self, _error):
        self._export_busy = False
        self.export_btn.setEnabled(True)
        self.show_message(
            "error",
            "Не удалось сохранить CSV-файл. Проверьте путь и права доступа."
            if self.lang == "RU" else "Could not save the CSV file. Check the path and permissions.",
        )

    def check_qbittorrent(self):
        if self._qbit_busy:
            return
        if not self.settings.get("qbit_enabled"):
            self.show_message("warning", TRANSLATIONS[self.lang]["qbit_disabled"])
            return
        if not config.QBIT_PASS:
            self.show_message("warning", "Пароль qBittorrent не сохранён в системном хранилище." if self.lang == "RU" else "The qBittorrent password is not available in the system keyring.")
            return

        self._qbit_busy = True
        self.qbit_btn.setEnabled(False)
        self.statusBar().showMessage("Подключение к qBittorrent…" if self.lang == "RU" else "Connecting to qBittorrent…")
        self._start_worker(
            lambda: qbittorrent_task(self.settings, config.QBIT_PASS),
            self._on_qbit_finished,
            self._on_qbit_error,
        )

    def _on_qbit_finished(self, torrents):
        self._qbit_busy = False
        self.qbit_btn.setEnabled(True)
        if not torrents:
            message = TRANSLATIONS[self.lang]["qbit_empty"]
        else:
            title = "Активные загрузки:\n\n" if self.lang == "RU" else "Active downloads:\n\n"
            message = title + "\n".join(torrents)
        self.show_message("info", message, title="qBittorrent")

    def _on_qbit_error(self, _error):
        self._qbit_busy = False
        self.qbit_btn.setEnabled(True)
        self.show_message("error", TRANSLATIONS[self.lang]["qbit_error"])

    def show_message(self, kind, message, title=None):
        title_map = {
            "error": TRANSLATIONS[self.lang]["error"],
            "warning": TRANSLATIONS[self.lang]["warning"],
            "success": TRANSLATIONS[self.lang]["success"],
            "info": "CineTrack",
        }
        dialog_title = title or title_map.get(kind, "CineTrack")
        if self._active_message is not None and self._active_message.isVisible():
            # A modal dialog runs a nested event loop. If another error arrives
            # meanwhile, update and raise the existing window instead of
            # creating a stack of nearly identical dialogs.
            self._active_message.set_content(dialog_title, message)
            self._active_message.raise_()
            self._active_message.activateWindow()
            return

        dialog = CustomMessageBox(self, dialog_title, message)
        self._active_message = dialog
        dialog.finished.connect(lambda _result, current=dialog: self._clear_message(current))
        dialog.exec_()

    def _clear_message(self, dialog):
        if self._active_message is dialog:
            self._active_message = None
