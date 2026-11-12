# Windows smoke-test checklist

Use a disposable media folder first. Do not use the only copy of a personal media collection for delete tests.

## First launch and settings

1. Create a Python 3.10+ environment, install `requirements.txt`, and run `py main.py`.
2. Complete the first-run Setup Wizard with qBittorrent disabled. Verify the main window opens.
3. Re-open CineTrack. Verify the first-run wizard does not appear again.
4. Open **Settings** from the main toolbar. Confirm the window has only TMDB API and qBittorrent sections; no page counter or Next/Back navigation.
5. Change the TMDB key, save, and run a search. Clear the key, save, restart, and verify that the source `.env` fallback is not silently re-enabled after an explicit clear.
6. Enable qBittorrent and enter the Web UI host, port, username, and password. Save and test the connection. Disable integration and save; verify the stored password is removed.

## Main features

7. Scan a test folder containing supported videos (`.mkv`, `.mp4`, `.avi`, `.webm`) and an unsupported file. Only supported videos should be added.
8. Scan the same folder again. The row count should not increase; the interface should remain responsive.
9. Select a record, search TMDB, and apply a result. Verify poster and year appear. Repeat with the network disconnected; the app should show an error without freezing.
10. Attach a poster, scan the folder again, and verify the record and poster remain. For legacy duplicate rows, one scan should merge duplicates while preserving poster metadata, reviews, and genre links.
11. Delete a library record. Verify the database entry and poster cache are removed but the original video file remains on disk.
12. Export CSV with Cyrillic names and open it in Excel or LibreOffice. Verify the text is readable.

## Build and installer

13. Run `build.bat`. It installs pinned build/runtime requirements, compiles the source, runs the automated tests, and builds `dist\CineTrack`.
14. Run `build_setup.bat` (or open `installer.iss` in Inno Setup and press F9). Verify `Output\CineTrack_Setup.exe` is created.
15. Install the setup on a test Windows account, launch CineTrack, and verify settings/database are created under the user's AppData directory.
16. Uninstall and verify the application is removed. User data in AppData should be handled deliberately before deleting it; do not assume uninstall removes it.

The automated suite checks the database/configuration layer and mocked worker logic. It does not replace this real Windows GUI, Keyring, TMDB, qBittorrent, and installer smoke test.
