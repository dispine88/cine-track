"""Apply the compact CineTrack settings dialog update to a local checkout.

The script can be placed either in the project root or in a helper folder.
It only edits the local working tree and never contacts GitHub.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def find_project_root() -> Path:
    candidates = [Path.cwd(), *SCRIPT_DIR.parents]
    for candidate in candidates:
        if (candidate / "gui" / "mainwindow.py").is_file():
            return candidate.resolve()
    raise SystemExit(
        "Could not find the CineTrack project root. Run this script from the "
        "project directory (the one containing gui/mainwindow.py)."
    )


def replace_once(source: str, old: str, new: str, description: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one match for {description}; found {count}. "
            "No project files have been changed. Your local source differs "
            "from the expected feature/raw-sql version."
        )
    return source.replace(old, new, 1)


def replace_import_block(source: str) -> str:
    if "from gui.settings_dialog import SettingsDialog" in source:
        raise RuntimeError(
            "SettingsDialog is already imported. The patch may already have "
            "been applied; no project files have been changed."
        )

    parenthesized = re.compile(
        r"(?ms)^from gui\.dialogs import\s*\(.*?^\)[ \t]*(?:\n|$)"
    )
    matches = list(parenthesized.finditer(source))
    if len(matches) == 1:
        old_block = matches[0].group(0)
    elif len(matches) == 0:
        # Also accept a one-line import, in case a formatter collapsed it.
        single_line = re.compile(r"(?m)^from gui\.dialogs import[^\n]*\n?")
        matches = list(single_line.finditer(source))
        if len(matches) != 1:
            raise RuntimeError(
                "Could not locate exactly one 'from gui.dialogs import' block. "
                "No project files have been changed. Inspect the imports at "
                "the top of gui/mainwindow.py."
            )
        old_block = matches[0].group(0)
    else:
        raise RuntimeError(
            f"Found {len(matches)} GUI dialog import blocks. "
            "No project files have been changed."
        )

    required = (
        "CustomInputDialog",
        "CustomMessageBox",
        "CustomTitleBar",
        "SearchDialog",
    )
    if not all(name in old_block for name in required):
        raise RuntimeError(
            "The dialog import block does not contain the expected CineTrack "
            "classes. No project files have been changed."
        )

    new_block = (
        "from gui.dialogs import (\n"
        "    CustomInputDialog, CustomMessageBox, CustomTitleBar, SearchDialog,\n"
        ")\n"
        "from gui.settings_dialog import SettingsDialog\n"
    )
    return source.replace(old_block, new_block, 1)


def find_dialog_source(root: Path) -> Path:
    candidates = (
        SCRIPT_DIR / "gui" / "settings_dialog.py",
        root / "CineTrack_settings_update" / "gui" / "settings_dialog.py",
        root / "gui" / "settings_dialog.py",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise SystemExit(
        "Could not find gui/settings_dialog.py. Extract the update ZIP into "
        "the project root first."
    )


def main() -> int:
    root = find_project_root()
    mainwindow = root / "gui" / "mainwindow.py"
    dialog_target = root / "gui" / "settings_dialog.py"
    dialog_source = find_dialog_source(root)
    backup = root / "gui" / "mainwindow.py.before_settings_patch.bak"

    if backup.exists():
        raise SystemExit(
            f"Backup already exists: {backup.name}. Refusing to overwrite it. "
            "Restore/rename the backup or inspect the previous patch first."
        )

    source = mainwindow.read_text(encoding="utf-8")

    # 1. Replace the old wizard import with the compact settings dialog.
    source = replace_import_block(source)

    # 2. Remove the gear button from the custom title bar.
    source = replace_once(
        source,
        '        self.title_bar = CustomTitleBar(self, "CineTrack - Local Media", settings_callback=self.open_settings)\n',
        '        self.title_bar = CustomTitleBar(self, "CineTrack - Local Media")\n',
        "title-bar settings button",
    )

    # 3. Add Settings beside the other main-toolbar actions.
    source = replace_once(
        source,
        "        self.export_btn = QPushButton()\n"
        "        self.export_btn.clicked.connect(self.export_to_csv)\n"
        "        self.lang_btn = QPushButton()\n",
        "        self.export_btn = QPushButton()\n"
        "        self.export_btn.clicked.connect(self.export_to_csv)\n"
        "        self.settings_btn = QPushButton()\n"
        "        self.settings_btn.clicked.connect(self.open_settings)\n"
        "        self.lang_btn = QPushButton()\n",
        "toolbar settings button",
    )
    source = replace_once(
        source,
        "                       self.qbit_btn, self.export_btn, self.lang_btn):\n",
        "                       self.qbit_btn, self.export_btn, self.settings_btn, self.lang_btn):\n",
        "toolbar button list",
    )
    source = replace_once(
        source,
        '        self.export_btn.setText(text["export"])\n',
        '        self.export_btn.setText(text["export"])\n'
        '        self.settings_btn.setText("⚙ Настройки" if self.lang == "RU" else "⚙ Settings")\n',
        "toolbar settings label",
    )

    # 4. Make the button open SettingsDialog, not SetupWizard.
    source = replace_once(
        source,
        '        """Open the setup wizard in edit mode and persist changed preferences."""\n'
        "        dialog = SetupWizard(self, initial_settings=self.settings, editing=True)\n",
        '        """Open the compact API/qBittorrent settings editor."""\n'
        "        dialog = SettingsDialog(self, self.settings)\n",
        "settings dialog constructor",
    )
    source = replace_once(
        source,
        '        tmdb_key = data.pop("tmdb_api_key", "").strip()\n'
        '        qbit_password = data.pop("qbit_pass", "")\n'
        '        if not data.get("qbit_enabled"):\n'
        '            qbit_password = ""\n',
        "        tmdb_key = dialog.tmdb_api_key\n"
        '        qbit_password = dialog.qbit_password if data.get("qbit_enabled") else ""\n',
        "settings secret values",
    )

    # All source checks succeeded. Stage the dialog file before mutating either target.
    dialog_content = dialog_source.read_text(encoding="utf-8")
    if not dialog_content.strip():
        raise SystemExit("The settings dialog source is empty; nothing was changed.")

    shutil.copy2(mainwindow, backup)
    try:
        if dialog_source != dialog_target.resolve():
            shutil.copy2(dialog_source, dialog_target)
        mainwindow.write_text(source, encoding="utf-8", newline="\n")
    except Exception:
        # Restore mainwindow if writing or copying unexpectedly fails.
        try:
            shutil.copy2(backup, mainwindow)
        except OSError:
            pass
        raise

    print("Settings UI update applied successfully.")
    print(f"Project: {root}")
    print(f"Backup:  {backup}")
    print(f"Dialog:  {dialog_target}")
    print("This script made local file changes only; GitHub was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
