"""Custom dialogs used by the CineTrack interface."""
from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QLineEdit, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

import config
from gui.workers import FunctionWorker, search_tmdb_task


class CustomTitleBar(QWidget):
    def __init__(self, parent, title_text="CineTrack", settings_callback=None):
        super().__init__(parent)
        self.parent_window = parent
        self._drag_position = None
        self.setFixedHeight(35)
        self.setStyleSheet(
            "background-color: #121212; color: #e0e0e0; "
            "border-bottom: 1px solid #333;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.title_label)
        layout.addStretch()

        # Keep Settings in the title bar so it remains visible even when
        # the main toolbar runs out of horizontal space.
        if settings_callback is not None:
            settings_button = QPushButton("⚙")
            settings_button.setFixedSize(30, 25)
            settings_button.setToolTip("Настройки / Settings")
            settings_button.setAccessibleName("Settings")
            settings_button.setStyleSheet(
                "QPushButton { background: transparent; border: none; font-size: 16px; }"
                "QPushButton:hover { background-color: #333; }"
            )
            settings_button.clicked.connect(settings_callback)
            layout.addWidget(settings_button)

        min_button = QPushButton("—")
        min_button.setFixedSize(30, 25)
        min_button.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 16px; }"
            "QPushButton:hover { background-color: #333; }"
        )
        min_button.clicked.connect(self.parent_window.showMinimized)
        layout.addWidget(min_button)

        close_button = QPushButton("✕")
        close_button.setFixedSize(30, 25)
        close_button.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 14px; }"
            "QPushButton:hover { background-color: #dc3545; color: white; }"
        )
        close_button.clicked.connect(self.parent_window.close)
        layout.addWidget(close_button)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPos() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_position is not None and event.buttons() & Qt.LeftButton:
            self.parent_window.move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        event.accept()


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

    def showEvent(self, event):
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None and parent.isVisible():
            center = parent.frameGeometry().center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
        else:
            screen = self.screen().availableGeometry()
            self.move(screen.center().x() - self.width() // 2,
                      screen.center().y() - self.height() // 2)


class CustomMessageBox(BaseDialog):
    def __init__(self, parent, title, text):
        super().__init__(parent, title)
        self.setFixedSize(400, 200)
        self.message_label = QLabel(text)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("font-size: 14px;")
        self.content_layout.addWidget(self.message_label)
        self.content_layout.addStretch()
        button = QPushButton("OK")
        button.setFixedWidth(100)
        button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(button)
        button_layout.addStretch()
        self.content_layout.addLayout(button_layout)

    def set_content(self, title, text):
        self.title_bar.title_label.setText(title)
        self.message_label.setText(text)


class CustomInputDialog(BaseDialog):
    def __init__(self, parent, title, label_text):
        super().__init__(parent, title)
        self.setFixedSize(400, 200)
        label = QLabel(label_text)
        label.setStyleSheet("font-size: 14px;")
        self.content_layout.addWidget(label)
        self.input_field = QLineEdit()
        self.input_field.returnPressed.connect(self.accept)
        self.content_layout.addWidget(self.input_field)
        self.content_layout.addStretch()
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("background-color: #333;")
        cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        self.content_layout.addLayout(button_layout)

    def get_text(self):
        return self.input_field.text()


class SearchDialog(BaseDialog):
    def __init__(self, parent=None, lang="RU"):
        super().__init__(parent, "Поиск / Search" if lang == "RU" else "Search")
        self.setFixedSize(600, 400)
        self.lang = lang
        self.selected_result = None
        self._active_worker = None

        top_layout = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItems(["TMDB", "Local (Локально)", "IMDB (Скоро)", "Netflix (Скоро)"])
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Введите название тайтла…" if lang == "RU" else "Enter a title…"
        )
        self.search_input.returnPressed.connect(self.perform_search)
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
        if not query or self._active_worker is not None:
            return
        if not config.TMDB_API_KEY:
            self.status_label.setText(
                "API-ключ TMDB не настроен." if self.lang == "RU" else "TMDB API key is not configured."
            )
            return
        if self.source_combo.currentText() != "TMDB":
            self.status_label.setText(
                "Этот источник пока не интегрирован." if self.lang == "RU" else "This source is not integrated yet."
            )
            return

        self.status_label.setText("Поиск…" if self.lang == "RU" else "Searching…")
        self.search_btn.setEnabled(False)
        self.results_list.clear()
        worker = FunctionWorker(search_tmdb_task, query, config.TMDB_API_KEY)
        self._active_worker = worker
        worker.signals.result.connect(self._on_search_result)
        worker.signals.error.connect(self._on_search_error)
        worker.signals.finished.connect(self._on_search_finished)
        QThreadPool.globalInstance().start(worker)

    def _on_search_result(self, results):
        if not results:
            self.status_label.setText("Ничего не найдено." if self.lang == "RU" else "No results found.")
            return
        self.status_label.setText(
            "Выберите подходящий результат:" if self.lang == "RU" else "Choose a result:"
        )
        for result in results:
            name = result.get("name") or result.get("title") or "Unknown title"
            date = result.get("first_air_date") or result.get("release_date") or ""
            year = date[:4] if date else "?"
            media_type = "TV" if result.get("media_type") == "tv" else "Movie"
            item = QListWidgetItem(f"{name} ({year}) [{media_type}]")
            item.setData(Qt.UserRole, result)
            self.results_list.addItem(item)

    def _on_search_error(self, _error_name):
        self.status_label.setText(
            "Не удалось связаться с TMDB. Проверьте соединение." if self.lang == "RU" else
            "TMDB is unavailable. Check your connection."
        )

    def _on_search_finished(self, _job_id):
        self._active_worker = None
        self.search_btn.setEnabled(True)

    def accept_selection(self, item):
        self.selected_result = item.data(Qt.UserRole)
        self.accept()


class SetupWizard(BaseDialog):
    def __init__(self, parent=None, initial_settings=None, editing=False):
        title = "CineTrack Settings" if editing else "CineTrack Setup"
        super().__init__(parent, title)
        self.setFixedSize(500, 450)
        self.is_editing = bool(editing)
        defaults = {
            "qbit_enabled": False,
            "qbit_host": "localhost",
            "qbit_port": 8080,
            "qbit_user": "admin",
            "language": "EN",
        }
        self.settings_data = {**defaults, **(initial_settings or {})}
        self.lang = self.settings_data.get("language", "EN")
        if self.lang not in ("RU", "EN"):
            self.lang = "EN"

        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)

        self.page1 = QWidget()
        page1_layout = QVBoxLayout(self.page1)
        self.welcome_label = QLabel()
        self.welcome_label.setAlignment(Qt.AlignCenter)
        page1_layout.addWidget(self.welcome_label)
        language_layout = QHBoxLayout()
        self.en_btn = QPushButton("English")
        self.ru_btn = QPushButton("Русский")
        self.en_btn.clicked.connect(lambda: self.set_lang("EN"))
        self.ru_btn.clicked.connect(lambda: self.set_lang("RU"))
        language_layout.addWidget(self.en_btn)
        language_layout.addWidget(self.ru_btn)
        page1_layout.addLayout(language_layout)
        self.stack.addWidget(self.page1)

        self.page_api = QWidget()
        api_layout = QVBoxLayout(self.page_api)
        self.api_label = QLabel()
        self.api_label.setOpenExternalLinks(True)
        self.api_label.setWordWrap(True)
        api_layout.addWidget(self.api_label)
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setText(config.TMDB_API_KEY)
        self.api_input.setPlaceholderText("Paste your API key here…")
        api_layout.addWidget(self.api_input)
        api_layout.addStretch()
        self.stack.addWidget(self.page_api)

        self.page_qbit = QWidget()
        qbit_layout = QVBoxLayout(self.page_qbit)
        self.qbit_cb = QCheckBox()
        qbit_layout.addWidget(self.qbit_cb)
        form = QFormLayout()
        self.host_input = QLineEdit("localhost")
        self.port_input = QLineEdit("8080")
        self.port_input.setValidator(QIntValidator(1, 65535, self.port_input))
        self.user_input = QLineEdit("admin")
        self.pass_input = QLineEdit(config.QBIT_PASS)
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.host_label = QLabel()
        self.port_label = QLabel()
        self.user_label = QLabel()
        self.pass_label = QLabel()
        form.addRow(self.host_label, self.host_input)
        form.addRow(self.port_label, self.port_input)
        form.addRow(self.user_label, self.user_input)
        form.addRow(self.pass_label, self.pass_input)
        qbit_layout.addLayout(form)
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #e57373;")
        qbit_layout.addWidget(self.validation_label)
        self.qbit_cb.toggled.connect(self.toggle_qbit_fields)
        self.stack.addWidget(self.page_qbit)

        self.page_finish = QWidget()
        finish_layout = QVBoxLayout(self.page_finish)
        self.finish_label = QLabel()
        self.finish_label.setAlignment(Qt.AlignCenter)
        finish_layout.addWidget(self.finish_label)
        self.stack.addWidget(self.page_finish)

        bottom_layout = QHBoxLayout()
        self.step_label = QLabel("< 1/4 >")
        self.step_label.setStyleSheet("color: gray;")
        self.back_btn = QPushButton()
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self.go_back)
        self.next_btn = QPushButton()
        self.next_btn.clicked.connect(self.go_next)
        bottom_layout.addWidget(self.step_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.back_btn)
        bottom_layout.addWidget(self.next_btn)
        self.content_layout.addLayout(bottom_layout)

        self.qbit_cb.setChecked(bool(self.settings_data.get("qbit_enabled", False)))
        self.host_input.setText(str(self.settings_data.get("qbit_host", "localhost")))
        self.port_input.setText(str(self.settings_data.get("qbit_port", 8080)))
        self.user_input.setText(str(self.settings_data.get("qbit_user", "admin")))
        self.toggle_qbit_fields(self.qbit_cb.isChecked())
        self.update_ui_text()

    def set_lang(self, lang):
        self.lang = lang
        self.settings_data["language"] = lang
        self.update_ui_text()

    def update_ui_text(self):
        if self.lang == "EN":
            self.welcome_label.setText("<h2>Welcome to CineTrack!</h2><p>Please choose your language:</p>")
            self.api_label.setText("<h2>TMDB API Key</h2><p>Optional: enter a key to fetch movie posters and metadata.</p><p>You can request a key at <a href='https://www.themoviedb.org/'>themoviedb.org</a>.</p>")
            self.api_input.setPlaceholderText("Paste your API key here…")
            self.qbit_cb.setText("Integrate with qBittorrent")
            self.host_label.setText("Host:")
            self.port_label.setText("Port:")
            self.user_label.setText("Username:")
            self.pass_label.setText("Password:")
            self.finish_label.setText("<h2>All set!</h2><p>Click Finish to save your settings.</p>")
            self.back_btn.setText("Back")
            if self.stack.currentIndex() == 3:
                self.next_btn.setText("Save" if self.is_editing else "Finish")
            else:
                self.next_btn.setText("Next")
        else:
            self.welcome_label.setText("<h2>Добро пожаловать в CineTrack!</h2><p>Выберите язык:</p>")
            self.api_label.setText("<h2>API-ключ TMDB</h2><p>Необязательно: ключ нужен для загрузки постеров и метаданных.</p><p>Его можно запросить на <a href='https://www.themoviedb.org/'>themoviedb.org</a>.</p>")
            self.api_input.setPlaceholderText("Вставьте API-ключ сюда…")
            self.qbit_cb.setText("Интегрировать с qBittorrent")
            self.host_label.setText("Хост:")
            self.port_label.setText("Порт:")
            self.user_label.setText("Логин:")
            self.pass_label.setText("Пароль:")
            self.finish_label.setText("<h2>Всё готово!</h2><p>Нажмите «Завершить», чтобы сохранить настройки.</p>")
            self.back_btn.setText("Назад")
            if self.stack.currentIndex() == 3:
                self.next_btn.setText("Сохранить" if self.is_editing else "Завершить")
            else:
                self.next_btn.setText("Далее")
        self.step_label.setText(f"< {self.stack.currentIndex() + 1}/4 >")

    def toggle_qbit_fields(self, checked=False):
        for widget in (self.host_input, self.port_input, self.user_input, self.pass_input):
            widget.setEnabled(bool(checked))

    def go_next(self):
        current = self.stack.currentIndex()
        if current < 3:
            self.stack.setCurrentIndex(current + 1)
            self.back_btn.setEnabled(True)
            self.update_ui_text()
            return

        qbit_enabled = self.qbit_cb.isChecked()
        if qbit_enabled:
            host = self.host_input.text().strip()
            port_text = self.port_input.text().strip()
            try:
                port = int(port_text)
            except ValueError:
                port = 0
            if not host or not 1 <= port <= 65535:
                self.validation_label.setText(
                    "Enter a host and a port from 1 to 65535." if self.lang == "EN" else
                    "Укажите хост и порт от 1 до 65535."
                )
                self.stack.setCurrentIndex(2)
                self.update_ui_text()
                return
            if not self.pass_input.text():
                self.validation_label.setText(
                    "Enter your qBittorrent Web UI password or disable the integration."
                    if self.lang == "EN" else
                    "Введите пароль Web UI qBittorrent или отключите интеграцию."
                )
                self.stack.setCurrentIndex(2)
                self.update_ui_text()
                return
        else:
            host, port = "localhost", 8080

        self.settings_data.update({
            "tmdb_api_key": self.api_input.text().strip(),
            "qbit_enabled": qbit_enabled,
            "qbit_host": host,
            "qbit_port": port,
            "qbit_user": self.user_input.text().strip() or "admin",
        })
        # An empty password means the user wants to remove the saved secret.
        self.settings_data["qbit_pass"] = self.pass_input.text() if qbit_enabled else ""
        self.accept()

    def go_back(self):
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self.back_btn.setEnabled(current - 1 > 0)
            self.validation_label.setText("")
            self.update_ui_text()
