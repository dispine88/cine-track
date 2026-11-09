import os
import sys
import subprocess
import re
import json
import requests
import qbittorrentapi
from io import BytesIO
from PIL import Image

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QLabel, QSplitter, 
                             QPushButton, QFileDialog, QMenu, QAbstractItemView, QDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage 

import config
from database import crud
from gui.constants import TRANSLATIONS
from gui.dialogs import CustomTitleBar, CustomMessageBox, CustomInputDialog, SearchDialog

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
        if os.path.exists(config.SETTINGS_FILE):
            with open(config.SETTINGS_FILE, 'r') as f:
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
        with open(config.SETTINGS_FILE, 'w') as f:
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
        
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        video_exts = ('.mkv', '.mp4', '.avi', '.webm')
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(video_exts):
                    full_path = os.path.join(root, file)
                    clean_name = self.clean_filename(file)
                    crud.add_title(name=clean_name, type="local", status="want", file_path=full_path)
                    
        self.update_ui_text()
        self.load_data()

    def add_manual(self):
        dialog = CustomInputDialog(self, "Добавить" if self.lang == "RU" else "Add", "Введите название:" if self.lang == "RU" else "Enter title:")
        if dialog.exec_() == QDialog.Accepted:
            text = dialog.get_text()
            if text:
                crud.add_title(name=text, type="manual", status="want")
                self.load_data()

    def delete_item(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: return
        msg = f"Удалить {len(selected_items)} записей?"
        
        dialog = CustomMessageBox(self, "Удаление", msg)
        if dialog.exec_() == QDialog.Accepted:
            for item in selected_items:
                title_id = item.data(Qt.UserRole)
                title = crud.get_title(title_id)
                if title:
                    if title.file_path and os.path.exists(title.file_path):
                        try: os.remove(title.file_path)
                        except Exception: pass
                    cache_path = os.path.join(config.CACHE_DIR, f"{title.id}.jpg")
                    if os.path.exists(cache_path):
                        try: os.remove(cache_path)
                        except Exception: pass
                    crud.delete_title(title_id)
            self.load_data()

    def load_data(self):
        self.list_widget.clear()
        titles = crud.get_all_titles()
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
        title = crud.get_title(title_id)
        
        if title:
            self.details_label.setText(f"<h3>{title.name}</h3><p><b>Тип:</b> {title.type} | <b>Год:</b> {title.year or '?'}</p>")
            
            cached_poster = os.path.join(config.CACHE_DIR, f"{title.id}.jpg")
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
            if config.CACHE_DIR in path:
                try: os.remove(path)
                except Exception: pass

    def open_search_dialog(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            CustomMessageBox(self, "Внимание", "Сначала выберите файл в списке!").exec_()
            return
            
        dialog = SearchDialog(self, self.lang)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_result:
            result = dialog.selected_result
            poster_path = result.get('poster_path')
            new_year = int((result.get('first_air_date') or result.get('release_date', '0'))[:4] or 0)
            
            if poster_path:
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                
                if not poster_url.startswith("https://image.tmdb.org/"):
                    print(f"Security Warning: Blocked download from untrusted URL: {poster_url}")
                    CustomMessageBox(self, "Ошибка безопасности", "Попытка скачать постер с недоверенного источника.").exec_()
                    return
                
                try:
                    response = requests.get(poster_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content)).convert("RGB")
                        
                        for item in selected_items:
                            title_id = item.data(Qt.UserRole)
                            img.save(os.path.join(config.CACHE_DIR, f"{title_id}.jpg"), "JPEG", quality=90)
                            crud.update_title_info(title_id, year=new_year, poster_url=poster_url)
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
        
        title_id = selected_items[0].data(Qt.UserRole)
        title = crud.get_title(title_id)
        
        if title and title.file_path:
            safe_path = os.path.abspath(title.file_path)
            
            if not os.path.isfile(safe_path):
                CustomMessageBox(self, "Ошибка", "Файл не найден или был перемещен.").exec_()
                return
            
            allowed_exts = ('.mkv', '.mp4', '.avi', '.webm')
            if not safe_path.lower().endswith(allowed_exts):
                CustomMessageBox(self, "Ошибка безопасности", "Недопустимый формат файла.").exec_()
                return

            try: 
                subprocess.Popen(["mpv", "--fs", safe_path])
            except FileNotFoundError: 
                if sys.platform == "win32":
                    os.startfile(safe_path)
                else:
                    subprocess.Popen(["xdg-open", safe_path])

    def check_qbittorrent(self):
        if not self.settings.get("qbit_enabled"):
            CustomMessageBox(self, "qBittorrent", "Интеграция отключена.").exec_()
            return
        
        conn_info = dict(
            host=self.settings["qbit_host"], 
            port=self.settings["qbit_port"], 
            username=self.settings["qbit_user"], 
            password=config.QBIT_PASS
        )
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