import sys
import os
import subprocess
import re
import requests
import json
import qbittorrentapi
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QListWidgetItem, 
                             QLabel, QSplitter, QPushButton, 
                             QFileDialog, QMessageBox, QInputDialog, QMenu, QAction,
                             QLineEdit, QAbstractItemView, QDialog, QFormLayout, 
                             QCheckBox, QDialogButtonBox, QStackedWidget, QComboBox)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap, QImage 
from db import get_session, Title, init_db

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
CACHE_DIR = os.path.expanduser("~/.cache/cinetrack_posters")
os.makedirs(CACHE_DIR, exist_ok=True)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 🚀 УНИВЕРСАЛЬНЫЙ ЗАГОЛОВОК ДЛЯ ВСЕХ ОКОН
class CustomTitleBar(QWidget):
    def __init__(self, parent, title_text="CineTrack"):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(35)
        self.setStyleSheet("background-color: #121212; color: #e0e0e0; border-bottom: 1px solid #333;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.title_label)
        layout.addStretch()
        
        btn_min = QPushButton("—")
        btn_min.setFixedSize(30, 25)
        btn_min.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 16px; } QPushButton:hover { background-color: #333; }")
        btn_min.clicked.connect(self.parent.showMinimized)
        layout.addWidget(btn_min)
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 25)
        btn_close.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 14px; } QPushButton:hover { background-color: #dc3545; color: white; }")
        btn_close.clicked.connect(self.parent.close)
        layout.addWidget(btn_close)

    def mousePressEvent(self, event):
        self.start_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'start_pos') and event.buttons() == Qt.LeftButton:
            delta = event.globalPos() - self.start_pos
            self.parent.move(self.parent.pos() + delta)
            self.start_pos = event.globalPos()

# 🚀 БАЗОВЫЙ КЛАСС ДЛЯ ВСЕХ ДИАЛОГОВЫХ ОКОН (Чтобы не повторяться)
class BaseDialog(QDialog):
    def __init__(self, parent=None, title="CineTrack"):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_bar = CustomTitleBar(self, title)
        self.main_layout.addWidget(self.title_bar)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.addWidget(self.content_widget)

# 🚀 КАСТОМНОЕ ОКНО СООБЩЕНИЙ (Замена QMessageBox)
class CustomMessageBox(BaseDialog):
    def __init__(self, parent, title, text, icon_type="info"):
        super().__init__(parent, title)
        self.setFixedSize(400, 200)
        
        msg_label = QLabel(text)
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setStyleSheet("font-size: 14px;")
        self.content_layout.addWidget(msg_label)
        self.content_layout.addStretch()
        
        btn = QPushButton("OK")
        btn.setFixedWidth(100)
        btn.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn)
        btn_layout.addStretch()
        self.content_layout.addLayout(btn_layout)

# 🚀 КАСТОМНОЕ ОКНО ВВОДА (Замена QInputDialog)
class CustomInputDialog(BaseDialog):
    def __init__(self, parent, title, label_text):
        super().__init__(parent, title)
        self.setFixedSize(400, 200)
        
        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 14px;")
        self.content_layout.addWidget(lbl)
        
        self.input_field = QLineEdit()
        self.content_layout.addWidget(self.input_field)
        self.content_layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #333;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        self.content_layout.addLayout(btn_layout)

    def get_text(self):
        return self.input_field.text()

# 🚀 ОКНО ПОИСКА
class SearchDialog(BaseDialog):
    def __init__(self, parent=None, lang="RU"):
        super().__init__(parent, "Поиск / Search" if lang == "RU" else "Search")
        self.setFixedSize(600, 400)
        self.lang = lang
        
        top_layout = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItems(["TMDB", "Local (Локально)", "IMDB (Скоро)", "Netflix (Скоро)"])
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите название тайтла..." if lang == "RU" else "Enter title...")
        
        self.search_btn = QPushButton("🔍 Искать" if lang == "RU" else "🔍 Search")
        self.search_btn.clicked.connect(self.perform_search)
        
        top_layout.addWidget(QLabel("Искать в:" if lang == "RU" else "Search in:"))
        top_layout.addWidget(self.source_combo)
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.search_btn)
        self.content_layout.addLayout(top_layout)
        
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.accept_selection)
        self.content_layout.addWidget(self.results_list)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.status_label)
        
        self.close_btn = QPushButton("Закрыть" if lang == "RU" else "Close")
        self.close_btn.clicked.connect(self.reject)
        self.content_layout.addWidget(self.close_btn)
        
        self.selected_result = None

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query:
            self.status_label.setText("Введите запрос!" if self.lang == "RU" else "Enter a query!")
            return
            
        source = self.source_combo.currentText()
        if "TMDB" not in source:
            self.status_label.setText("Эта база данных пока не интегрирована.")
            return

        self.status_label.setText("Выполняется поиск, подождите...")
        self.search_btn.setEnabled(False)
        self.results_list.clear()
        QApplication.processEvents()
        
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={requests.utils.quote(query)}"
        
        try:
            response = requests.get(url)
            results = response.json().get('results', [])
            
            if not results:
                self.status_label.setText("Ничего не найдено.")
                return
                
            self.status_label.setText("Поиск успешен. Выберите результат:")
            
            for res in results[:10]:
                name = res.get('name') or res.get('title')
                date = res.get('first_air_date') or res.get('release_date', '')
                year = date[:4] if date else "?"
                media_type = "TV" if res.get('media_type') == 'tv' else "Movie"
                display = f"{name} ({year}) [{media_type}]"
                
                item = QListWidgetItem(display)
                item.setData(Qt.UserRole, res)
                self.results_list.addItem(item)
                
        except Exception as e:
            self.status_label.setText(f"Ошибка: {e}")
        finally:
            self.search_btn.setEnabled(True)

    def accept_selection(self, item):
        self.selected_result = item.data(Qt.UserRole)
        self.accept()

# 🚀 ВИЗАРД
class SetupWizard(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent, "CineTrack Setup")
        self.setFixedSize(500, 400)
        
        self.lang = "EN"
        self.settings_data = {"qbit_enabled": False, "qbit_host": "localhost", "qbit_port": 8080, "qbit_user": "admin", "qbit_pass": "adminadmin", "language": "EN"}
        
        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)
        
        self.page1 = QWidget()
        p1_layout = QVBoxLayout(self.page1)
        self.welcome_label = QLabel("<h2>Welcome to CineTrack!</h2><p>Please choose your language:</p>")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        p1_layout.addWidget(self.welcome_label)
        
        btn_layout = QHBoxLayout()
        self.en_btn = QPushButton("English")
        self.ru_btn = QPushButton("Русский")
        self.en_btn.clicked.connect(lambda: self.set_lang("EN"))
        self.ru_btn.clicked.connect(lambda: self.set_lang("RU"))
        btn_layout.addWidget(self.en_btn)
        btn_layout.addWidget(self.ru_btn)
        p1_layout.addLayout(btn_layout)
        self.stack.addWidget(self.page1)
        
        self.page2 = QWidget()
        p2_layout = QVBoxLayout(self.page2)
        self.qbit_cb = QCheckBox("Интегрировать с qBittorrent")
        self.qbit_cb.setChecked(False)
        p2_layout.addWidget(self.qbit_cb)
        
        form = QFormLayout()
        self.host_input = QLineEdit("localhost")
        self.port_input = QLineEdit("8080")
        self.user_input = QLineEdit("admin")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        form.addRow("Хост:", self.host_input)
        form.addRow("Порт:", self.port_input)
        form.addRow("Логин:", self.user_input)
        form.addRow("Пароль:", self.pass_input)
        p2_layout.addLayout(form)
        
        self.qbit_cb.toggled.connect(self.toggle_qbit_fields)
        self.stack.addWidget(self.page2)
        
        self.page3 = QWidget()
        p3_layout = QVBoxLayout(self.page3)
        self.finish_label = QLabel("<h2>Всё готово!</h2><p>Нажмите 'Завершить', чтобы начать работу.</p>")
        self.finish_label.setAlignment(Qt.AlignCenter)
        p3_layout.addWidget(self.finish_label)
        self.stack.addWidget(self.page3)
        
        bottom_layout = QHBoxLayout()
        self.step_label = QLabel("< 1/3 >")
        self.step_label.setStyleSheet("color: gray;")
        
        self.back_btn = QPushButton("Назад")
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self.go_back)
        
        self.next_btn = QPushButton("Далее")
        self.next_btn.clicked.connect(self.go_next)
        
        bottom_layout.addWidget(self.step_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.back_btn)
        bottom_layout.addWidget(self.next_btn)
        self.content_layout.addLayout(bottom_layout)
        
        self.update_ui_text()

    def set_lang(self, lang):
        self.lang = lang
        self.settings_data["language"] = lang
        self.update_ui_text()

    def update_ui_text(self):
        if self.lang == "EN":
            self.welcome_label.setText("<h2>Welcome to CineTrack!</h2><p>Please choose your language:</p>")
            self.qbit_cb.setText("Integrate with qBittorrent")
            self.finish_label.setText("<h2>All set!</h2><p>Click 'Finish' to start.</p>")
            self.back_btn.setText("Back")
            self.next_btn.setText("Next" if self.stack.currentIndex() < 2 else "Finish")
        else:
            self.welcome_label.setText("<h2>Добро пожаловать в CineTrack!</h2><p>Пожалуйста, выберите язык:</p>")
            self.qbit_cb.setText("Интегрировать с qBittorrent")
            self.finish_label.setText("<h2>Всё готово!</h2><p>Нажмите 'Завершить', чтобы начать работу.</p>")
            self.back_btn.setText("Назад")
            self.next_btn.setText("Далее" if self.stack.currentIndex() < 2 else "Завершить")

    def toggle_qbit_fields(self):
        state = self.qbit_cb.isChecked()
        self.host_input.setEnabled(state)
        self.port_input.setEnabled(state)
        self.user_input.setEnabled(state)
        self.pass_input.setEnabled(state)

    def go_next(self):
        current = self.stack.currentIndex()
        if current < 2:
            self.stack.setCurrentIndex(current + 1)
            self.step_label.setText(f"< {current + 2}/3 >")
            self.back_btn.setEnabled(True)
            self.update_ui_text()
        else:
            self.settings_data["qbit_enabled"] = self.qbit_cb.isChecked()
            self.settings_data["qbit_host"] = self.host_input.text()
            self.settings_data["qbit_port"] = int(self.port_input.text() or 8080)
            self.settings_data["qbit_user"] = self.user_input.text()
            self.settings_data["qbit_pass"] = self.pass_input.text()
            self.accept()

    def go_back(self):
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self.step_label.setText(f"< {current}/3 >")
            if current == 1:
                self.back_btn.setEnabled(False)
            self.update_ui_text()

TRANSLATIONS = {
    "RU": {
        "scan": "📁 Сканировать", "add": "➕ Добавить", "search": "🔍 Поиск",
        "play": "▶️ Воспроизвести", "no_poster": "Нет обложки",
        "select_file": "Выберите файл", "delete": "Удалить",
        "play_ctx": "Воспроизвести", "qbit": "🧲 qBittorrent"
    },
    "EN": {
        "scan": "📁 Scan", "add": "➕ Add", "search": "🔍 Search",
        "play": "▶️ Play", "no_poster": "No Poster",
        "select_file": "Select File", "delete": "Delete",
        "play_ctx": "Play", "qbit": "🧲 qBittorrent"
    }
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CineTrack - Local Media")
        self.resize(1100, 750)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        
        self.settings = self.load_settings()
        self.lang = self.settings.get("language", "RU")
        
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
        
        self.lang_btn = QPushButton("EN" if self.lang == "RU" else "RU")
        self.lang_btn.setFixedWidth(50)
        self.lang_btn.clicked.connect(self.toggle_language)
        
        top_layout.addWidget(self.scan_btn)
        top_layout.addWidget(self.add_btn)
        top_layout.addWidget(self.search_btn)
        top_layout.addWidget(self.qbit_btn)
        top_layout.addWidget(self.lang_btn)
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
        
        self.update_ui_text()
        self.load_data()

    def load_settings(self):
        if os.path.exists('settings.json'):
            with open('settings.json', 'r') as f:
                return json.load(f)
        return {}

    def update_ui_text(self):
        t = TRANSLATIONS[self.lang]
        self.scan_btn.setText(t["scan"])
        self.add_btn.setText(t["add"])
        self.search_btn.setText(t["search"])
        self.play_btn.setText(t["play"])
        self.qbit_btn.setText(t["qbit"])
        self.poster_label.setText(t["no_poster"])
        self.details_label.setText(f"<h2>{t['select_file']}</h2>")
        self.lang_btn.setText("EN" if self.lang == "RU" else "RU")

    def toggle_language(self):
        self.lang = "EN" if self.lang == "RU" else "RU"
        self.settings["language"] = self.lang
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)
        self.update_ui_text()
        self.load_data()

    def clean_filename(self, filename):
        name = os.path.splitext(filename)[0]
        name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
        name = name.replace('_', ' ').replace('.', ' ')
        return re.sub(' +', ' ', name).strip()

    def scan_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку" if self.lang == "RU" else "Select Folder")
        if not folder: return
        self.scan_btn.setText("...")
        QApplication.processEvents()
        
        video_exts = ('.mkv', '.mp4', '.avi', '.webm')
        with get_session() as session:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(video_exts):
                        full_path = os.path.join(root, file)
                        existing = session.query(Title).filter_by(file_path=full_path).first()
                        if not existing:
                            clean_name = self.clean_filename(file)
                            new_title = Title(name=clean_name, type="local", status="want", file_path=full_path)
                            session.add(new_title)
            session.commit()
        self.update_ui_text()
        self.load_data()

    def add_manual(self):
        # 🚀 Используем наш кастомный инпут
        dialog = CustomInputDialog(self, "Добавить" if self.lang == "RU" else "Add", "Введите название:" if self.lang == "RU" else "Enter title:")
        if dialog.exec_() == QDialog.Accepted:
            text = dialog.get_text()
            if text:
                with get_session() as session:
                    session.add(Title(name=text, type="manual", status="want"))
                    session.commit()
                self.load_data()

    def delete_item(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: return
        msg = f"Удалить {len(selected_items)} записей?"
        
        # 🚀 Используем наш кастомный месседжбокс
        dialog = CustomMessageBox(self, "Удаление", msg)
        if dialog.exec_() == QDialog.Accepted:
            with get_session() as session:
                for item in selected_items:
                    title = session.get(Title, item.data(Qt.UserRole))
                    if title:
                        if title.file_path and os.path.exists(title.file_path):
                            try: os.remove(title.file_path)
                            except Exception: pass
                        cache_path = os.path.join(CACHE_DIR, f"{title.id}.jpg")
                        if os.path.exists(cache_path):
                            try: os.remove(cache_path)
                            except Exception: pass
                        session.delete(title)
                session.commit()
            self.load_data()

    def load_data(self):
        self.list_widget.clear()
        with get_session() as session:
            titles = session.query(Title).order_by(Title.name).all()
            for title in titles:
                year_str = f" ({title.year})" if title.year else ""
                display_text = f"{title.name}{year_str} [{title.type}]"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, title.id)
                self.list_widget.addItem(item)

    def on_item_selected(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            self.play_btn.setEnabled(False)
            return
            
        self.play_btn.setEnabled(True)
        title_id = selected_items[0].data(Qt.UserRole)
        
        with get_session() as session:
            title = session.get(Title, title_id)
            if title:
                self.details_label.setText(f"<h3>{title.name}</h3><p><b>Тип:</b> {title.type} | <b>Год:</b> {title.year or '?'}</p>")
                
                cached_poster = os.path.join(CACHE_DIR, f"{title.id}.jpg")
                local_poster = self.find_local_poster(title.file_path)
                
                if local_poster:
                    self.load_local_image(local_poster)
                elif os.path.exists(cached_poster):
                    self.load_local_image(cached_poster)
                else:
                    self.poster_label.clear()
                    self.poster_label.setText(TRANSLATIONS[self.lang]["no_poster"])

    def find_local_poster(self, file_path):
        if not file_path: return None
        folder = os.path.dirname(file_path)
        for name in ["poster.jpg", "cover.jpg", "folder.jpg", "poster.png", "cover.png"]:
            path = os.path.join(folder, name)
            if os.path.exists(path): return path
        return None

    def load_local_image(self, path):
        try:
            img = Image.open(path).convert("RGBA")
            qim = QImage(img.tobytes("raw", "RGBA"), img.size[0], img.size[1], QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qim)
            if not pixmap.isNull():
                self.poster_label.setPixmap(pixmap.scaled(400, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.poster_label.setText("Error")
            if CACHE_DIR in path:
                try: os.remove(path)
                except Exception: pass

    def open_search_dialog(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            # 🚀 Кастомное предупреждение
            CustomMessageBox(self, "Внимание", "Сначала выберите файл в списке!").exec_()
            return
            
        dialog = SearchDialog(self, self.lang)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_result:
            result = dialog.selected_result
            poster_path = result.get('poster_path')
            new_year = int((result.get('first_air_date') or result.get('release_date', '0'))[:4] or 0)
            
            if poster_path:
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                try:
                    response = requests.get(poster_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content)).convert("RGB")
                        
                        with get_session() as session:
                            for item in selected_items:
                                title = session.get(Title, item.data(Qt.UserRole))
                                if title:
                                    img.save(os.path.join(CACHE_DIR, f"{title.id}.jpg"), "JPEG", quality=90)
                                    title.year = new_year
                                    title.poster_url = poster_url
                            session.commit()
                except Exception as e:
                    print(f"Error downloading poster: {e}")
            self.load_data()
            self.on_item_selected()

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        self.list_widget.setCurrentItem(item)
        menu = QMenu(self)
        menu.addAction(TRANSLATIONS[self.lang]["play_ctx"], self.play_video)
        menu.addSeparator()
        menu.addAction(TRANSLATIONS[self.lang]["delete"], self.delete_item)
        menu.exec_(self.list_widget.viewport().mapToGlobal(pos))

    def play_video(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: return
        with get_session() as session:
            title = session.get(Title, selected_items[0].data(Qt.UserRole))
            if title and title.file_path:
                try: 
                    subprocess.Popen(["mpv", "--fs", title.file_path])
                except FileNotFoundError: 
                    if sys.platform == "win32":
                        os.startfile(title.file_path)
                    else:
                        subprocess.Popen(["xdg-open", title.file_path])

    def check_qbittorrent(self):
        if not self.settings.get("qbit_enabled"):
            CustomMessageBox(self, "qBittorrent", "Интеграция отключена.").exec_()
            return
        conn_info = dict(host=self.settings["qbit_host"], port=self.settings["qbit_port"], username=self.settings["qbit_user"], password=self.settings["qbit_pass"])
        try:
            with qbittorrentapi.Client(**conn_info) as qbt_client:
                torrents = qbt_client.torrents_info()
                if not torrents:
                    CustomMessageBox(self, "qBittorrent", "Список торрентов пуст.").exec_()
                    return
                msg = "Активные загрузки:\n\n" + "\n".join([f"[{round(t.progress * 100, 1)}%] {t.name}" for t in torrents[:10]])
                CustomMessageBox(self, "qBittorrent", msg).exec_()
        except Exception as e:
            CustomMessageBox(self, "Ошибка", f"Не удалось подключиться.\n\n{e}").exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    qss_path = resource_path("style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())
            
    init_db()
    
    if not os.path.exists("settings.json"):
        wizard = SetupWizard()
        if wizard.exec_() == QDialog.Accepted:
            with open("settings.json", "w") as f:
                json.dump(wizard.settings_data, f, indent=4)
        else:
            sys.exit(0)
            
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())