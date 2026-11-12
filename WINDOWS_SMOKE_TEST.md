# Windows smoke-test checklist

Run this after extracting the maintenance archive over your existing checkout and rebuilding the installer.

1. Create/activate the project virtual environment and install `requirements.txt`.
2. Run `py main.py`. On first run, switch RU/EN in the Setup Wizard, leave TMDB empty, leave qBittorrent disabled, finish setup, and verify the local library window opens.
3. Re-run and verify the wizard does not appear again. Check that `settings.json` contains ordinary settings only and secrets are in Windows Credential Manager.
4. Scan a test folder containing a few supported videos and one unsupported file. Verify the supported files appear and the unsupported file does not.
5. Scan the same folder again. Verify that no duplicate entries are added and the window remains responsive during scanning.
6. Select a local video and use Delete. Verify the entry disappears from CineTrack but the original video remains on disk.
7. With a valid TMDB key and network access, search for a known title and apply a result. Verify the poster is cached and the year is updated. Repeat with network access disabled: the interface should remain responsive and show an error.
8. Export the library to CSV. Verify the file opens correctly in Excel/LibreOffice and includes UTF-8 text.
9. If qBittorrent Web UI is configured, test a successful connection. Then stop the Web UI and verify CineTrack reports an error without freezing for an extended period.
10. Build with `build.bat`, compile `installer.iss` in Inno Setup, install the result, launch it, and verify the database/settings are created under the user's AppData directory.

Do not use a real media library for the first deletion test. Use a disposable test folder.

## Settings editing and duplicate regression

- Open Settings from the main window after first-run setup; change the TMDB key and confirm Search uses the new key without deleting settings.json.
- Change qBittorrent host, port, username, and password; verify the new credentials are used. Disable qBittorrent and confirm the stored password is removed.
- Scan a folder, attach a TMDB poster to one video, then scan the same folder again. The row count should not increase and the poster should remain attached.
- If older duplicate rows already exist for the same physical path, run one folder scan; duplicate rows should merge, preserving the record with poster metadata, reviews, and genre links.
