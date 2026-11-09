import sys
import os
import json
import keyring
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtGui import QIcon

import config
from database.db import init_db
from gui.mainwindow import MainWindow
from gui.dialogs import SetupWizard

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    qss_path = resource_path("style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())
            
    init_db()
    
    if not os.path.exists(config.SETTINGS_FILE):
        wizard = SetupWizard()
        if wizard.exec_() == QDialog.Accepted:
            data = wizard.settings_data.copy()
            
            if data.get("tmdb_api_key"):
                keyring.set_password("CineTrack", "tmdb_api_key", data["tmdb_api_key"])
                config.TMDB_API_KEY = data["tmdb_api_key"]
                del data["tmdb_api_key"]
                
            if data.get("qbit_pass"):
                keyring.set_password("CineTrack", "qbit_pass", data["qbit_pass"])
                del data["qbit_pass"]
                
            with open(config.SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        else:
            sys.exit(0)
            
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())