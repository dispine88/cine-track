"""Compact editor for TMDB and qBittorrent settings."""
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

import config
from gui.dialogs import BaseDialog


class SettingsDialog(BaseDialog):
    """Edit API credentials and qBittorrent connection details in one window."""

    def __init__(self, parent=None, initial_settings=None):
        settings = dict(initial_settings or {})
        self.lang = settings.get("language", getattr(parent, "lang", "RU"))
        if self.lang not in ("RU", "EN"):
            self.lang = "RU"

        super().__init__(parent, "Настройки" if self.lang == "RU" else "Settings")
        self.setFixedSize(560, 455)
        self.settings_data = {
            key: value for key, value in settings.items()
            if key not in ("tmdb_api_key", "qbit_pass")
        }

        api_group = QGroupBox("TMDB API")
        api_form = QFormLayout(api_group)
        self.api_input = QLineEdit(config.TMDB_API_KEY)
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setPlaceholderText(
            "Вставьте API-ключ" if self.lang == "RU" else "Paste API key"
        )
        self.api_hint = QLabel(
            "Оставьте поле пустым, чтобы удалить сохранённый ключ."
            if self.lang == "RU" else
            "Leave the field empty to remove the saved key."
        )
        self.api_hint.setWordWrap(True)
        api_form.addRow("API key:", self.api_input)
        api_form.addRow("", self.api_hint)
        self.content_layout.addWidget(api_group)

        qbit_group = QGroupBox("qBittorrent")
        qbit_layout = QVBoxLayout(qbit_group)
        self.qbit_enabled = QCheckBox(
            "Включить интеграцию" if self.lang == "RU" else "Enable integration"
        )
        self.qbit_enabled.setChecked(bool(settings.get("qbit_enabled", False)))
        qbit_layout.addWidget(self.qbit_enabled)

        qbit_form = QFormLayout()
        self.host_input = QLineEdit(str(settings.get("qbit_host", "localhost")))
        self.port_input = QLineEdit(str(settings.get("qbit_port", 8080)))
        self.port_input.setValidator(QIntValidator(1, 65535, self.port_input))
        self.user_input = QLineEdit(str(settings.get("qbit_user", "admin")))
        self.password_input = QLineEdit(config.QBIT_PASS)
        self.password_input.setEchoMode(QLineEdit.Password)

        labels = (
            ("Хост:", "Порт:", "Имя пользователя:", "Пароль:")
            if self.lang == "RU" else
            ("Host:", "Port:", "Username:", "Password:")
        )
        for label, field in zip(
            labels,
            (self.host_input, self.port_input, self.user_input, self.password_input),
        ):
            qbit_form.addRow(label, field)
        qbit_layout.addLayout(qbit_form)
        self.content_layout.addWidget(qbit_group)

        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #e57373;")
        self.validation_label.setWordWrap(True)
        self.content_layout.addWidget(self.validation_label)
        self.qbit_enabled.toggled.connect(self._toggle_qbit_fields)
        self._toggle_qbit_fields(self.qbit_enabled.isChecked())

        self.content_layout.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_button = QPushButton("Отмена" if self.lang == "RU" else "Cancel")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("Сохранить" if self.lang == "RU" else "Save")
        save_button.setDefault(True)
        save_button.clicked.connect(self._save)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)
        self.content_layout.addLayout(buttons)

    def _toggle_qbit_fields(self, enabled):
        for widget in (
            self.host_input,
            self.port_input,
            self.user_input,
            self.password_input,
        ):
            widget.setEnabled(bool(enabled))

    def _save(self):
        qbit_enabled = self.qbit_enabled.isChecked()
        host = self.host_input.text().strip()
        username = self.user_input.text().strip() or "admin"
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            port = 0

        if qbit_enabled and (not host or not 1 <= port <= 65535):
            self.validation_label.setText(
                "Укажите хост и порт от 1 до 65535." if self.lang == "RU" else
                "Enter a host and a port from 1 to 65535."
            )
            return
        if qbit_enabled and not self.password_input.text():
            self.validation_label.setText(
                "Введите пароль Web UI qBittorrent." if self.lang == "RU" else
                "Enter the qBittorrent Web UI password."
            )
            return
        if not host:
            host = "localhost"
        if not 1 <= port <= 65535:
            port = 8080

        self.settings_data.update({
            "qbit_enabled": qbit_enabled,
            "qbit_host": host,
            "qbit_port": port,
            "qbit_user": username,
        })
        self.tmdb_api_key = self.api_input.text().strip()
        if self.tmdb_api_key:
            self.settings_data.pop("tmdb_api_key_disabled", None)
        else:
            # Explicitly clearing the key must also disable a source-only .env fallback.
            self.settings_data["tmdb_api_key_disabled"] = True
        self.qbit_password = self.password_input.text() if qbit_enabled else ""
        self.accept()
