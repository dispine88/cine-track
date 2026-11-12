"""CineTrack application entry point."""
import os
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

import config
from database.db import init_db
from gui.dialogs import SetupWizard
from gui.mainwindow import MainWindow


def resource_path(relative_path):
    """Resolve bundled resources both in source and PyInstaller builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    return str(base_path / relative_path)


def configure_first_run(parent=None):
    if config.SETTINGS_FILE.exists() and config.load_settings():
        return True

    wizard = SetupWizard(parent)
    if wizard.exec_() != QDialog.Accepted:
        return False

    data = wizard.settings_data.copy()
    tmdb_key = data.pop("tmdb_api_key", "")
    qbit_password = data.pop("qbit_pass", "")

    keyring_errors = []
    try:
        # Replace a supplied key, or remove an old one when the user cleared it.
        if tmdb_key or config.get_secret("tmdb_api_key"):
            config.set_secret("tmdb_api_key", tmdb_key)
    except Exception:
        keyring_errors.append("TMDB API key")
    try:
        new_qbit_password = qbit_password if data.get("qbit_enabled") else ""
        if new_qbit_password or config.get_secret("qbit_pass"):
            config.set_secret("qbit_pass", new_qbit_password)
    except Exception:
        keyring_errors.append("qBittorrent password")
        data["qbit_enabled"] = False
    config.reload_secrets()

    try:
        config.save_settings(data)
    except OSError as exc:
        QMessageBox.critical(
            parent,
            "CineTrack",
            f"Не удалось сохранить настройки. Проверьте права доступа к папке приложения.\n{exc}",
        )
        return False

    if keyring_errors:
        QMessageBox.warning(
            parent,
            "CineTrack",
            "Не удалось сохранить секреты в системном хранилище: "
            + ", ".join(keyring_errors)
            + ". Приложение запустится, но соответствующие интеграции будут недоступны до настройки Keyring.",
        )
    return True


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CineTrack")
    app.setOrganizationName("CineTrack")

    qss_path = resource_path("style.qss")
    if os.path.isfile(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as stream:
                app.setStyleSheet(stream.read())
        except OSError:
            pass

    try:
        init_db()
        if not configure_first_run():
            return 0
        window = MainWindow()
        window.show()
        return app.exec_()
    except Exception as exc:
        QMessageBox.critical(
            None,
            "CineTrack — startup error",
            "Не удалось запустить приложение. Проверьте настройки и доступ к файлам.\n\n"
            f"Тип ошибки: {type(exc).__name__}",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
