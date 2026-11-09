import requests
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QDialog, QFormLayout, 
                             QCheckBox, QComboBox, QListWidget, QListWidgetItem, 
                             QStackedWidget, QApplication)
from PyQt5.QtCore import Qt
import config

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

class CustomMessageBox(BaseDialog):
    def __init__(self, parent, title, text):
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

class SearchDialog(BaseDialog):
    def __init__(self, parent=None, lang="RU"):
        super().__init__(parent, "Поиск / Search" if lang == "RU" else "Search")
        self.setFixedSize(600, 400)
        self.lang = lang
        self.selected_result = None
        
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

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query: return
            
        if not config.TMDB_API_KEY:
            self.status_label.setText("Ошибка: API ключ не найден в .env")
            return
            
        source = self.source_combo.currentText()
        if "TMDB" not in source:
            self.status_label.setText("Эта база данных пока не интегрирована.")
            return

        self.status_label.setText("Выполняется поиск, подождите...")
        self.search_btn.setEnabled(False)
        self.results_list.clear()
        
        QApplication.processEvents()
        
        url = f"https://api.themoviedb.org/3/search/multi?api_key={config.TMDB_API_KEY}&query={requests.utils.quote(query)}"
        
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
                
                item = QListWidgetItem(f"{name} ({year}) [{media_type}]")
                item.setData(Qt.UserRole, res)
                self.results_list.addItem(item)
                
        except Exception as e:
            self.status_label.setText(f"Ошибка: {e}")
        finally:
            self.search_btn.setEnabled(True)

    def accept_selection(self, item):
        self.selected_result = item.data(Qt.UserRole)
        self.accept()

class SetupWizard(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent, "CineTrack Setup")
        self.setFixedSize(500, 450) # Сделали чуть выше
        
        self.lang = "EN"
        self.settings_data = {
            "qbit_enabled": False, "qbit_host": "localhost", "qbit_port": 8080, 
            "qbit_user": "admin", "qbit_pass": "adminadmin", "language": "EN", "tmdb_api_key": ""
        }
        
        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)
        
        # --- СТРАНИЦА 1: Язык ---
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
        
        # --- СТРАНИЦА 2: API Key ---
        self.page_api = QWidget()
        p_api_layout = QVBoxLayout(self.page_api)
        self.api_label = QLabel("<h2>TMDB API Key</h2><p>Please enter your TMDB API key to fetch posters. You can get it for free at <a href='https://www.themoviedb.org/'>themoviedb.org</a>.</p>")
        self.api_label.setOpenExternalLinks(True)
        self.api_label.setWordWrap(True)
        p_api_layout.addWidget(self.api_label)
        
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Paste your API key here...")
        p_api_layout.addWidget(self.api_input)
        p_api_layout.addStretch()
        self.stack.addWidget(self.page_api)

        # --- СТРАНИЦА 3: qBittorrent ---
        self.page2 = QWidget()
        p2_layout = QVBoxLayout(self.page2)
        self.qbit_cb = QCheckBox("Интегрировать с qBittorrent")
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
        
        # --- СТРАНИЦА 4: Финиш ---
        self.page3 = QWidget()
        p3_layout = QVBoxLayout(self.page3)
        self.finish_label = QLabel("<h2>Всё готово!</h2><p>Нажмите 'Завершить'.</p>")
        self.finish_label.setAlignment(Qt.AlignCenter)
        p3_layout.addWidget(self.finish_label)
        self.stack.addWidget(self.page3)
        
        # --- НИЖНЯЯ ПАНЕЛЬ ---
        bottom_layout = QHBoxLayout()
        self.step_label = QLabel("< 1/4 >")
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
            self.api_label.setText("<h2>TMDB API Key</h2><p>Please enter your TMDB API key to fetch posters. You can get it for free at <a href='https://www.themoviedb.org/'>themoviedb.org</a>.</p>")
            self.api_input.setPlaceholderText("Paste your API key here...")
            self.qbit_cb.setText("Integrate with qBittorrent")
            self.finish_label.setText("<h2>All set!</h2><p>Click 'Finish'.</p>")
            self.back_btn.setText("Back")
            self.next_btn.setText("Next" if self.stack.currentIndex() < 3 else "Finish")
        else:
            self.welcome_label.setText("<h2>Добро пожаловать в CineTrack!</h2><p>Выберите язык:</p>")
            self.api_label.setText("<h2>API Ключ TMDB</h2><p>Введите ваш API ключ от TMDB, чтобы загружать постеры. Его можно получить бесплатно на сайте <a href='https://www.themoviedb.org/'>themoviedb.org</a>.</p>")
            self.api_input.setPlaceholderText("Вставьте ваш ключ сюда...")
            self.qbit_cb.setText("Интегрировать с qBittorrent")
            self.finish_label.setText("<h2>Всё готово!</h2><p>Нажмите 'Завершить'.</p>")
            self.back_btn.setText("Назад")
            self.next_btn.setText("Далее" if self.stack.currentIndex() < 3 else "Завершить")

    def toggle_qbit_fields(self):
        state = self.qbit_cb.isChecked()
        self.host_input.setEnabled(state)
        self.port_input.setEnabled(state)
        self.user_input.setEnabled(state)
        self.pass_input.setEnabled(state)

    def go_next(self):
        current = self.stack.currentIndex()
        if current < 3:
            self.stack.setCurrentIndex(current + 1)
            self.step_label.setText(f"< {current + 2}/4 >")
            self.back_btn.setEnabled(True)
            self.update_ui_text()
        else:
            # Сохраняем ключ API
            self.settings_data["tmdb_api_key"] = self.api_input.text().strip()
            
            # Сохраняем qBit
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
            self.step_label.setText(f"< {current}/4 >")
            if current == 1:
                self.back_btn.setEnabled(False)
            self.update_ui_text()