# Maintenance notes

## Changes in this maintenance build

- Moved folder scanning, TMDB search, poster downloads, and qBittorrent requests to `QThreadPool` workers.
- Added connect/read timeouts to TMDB and qBittorrent HTTP calls.
- Changed folder import to a single SQLite transaction with path de-duplication.
- Ensured SQLite connections enable foreign keys, apply a busy timeout, and are always closed.
- Added missing CRUD functions for genres, title-genre associations, and reviews.
- Deleting a media-library entry no longer deletes the original video file; it removes metadata and the cached poster only.
- Fixed Setup Wizard port validation and disabled qBittorrent fields when integration is off.
- Removed the default qBittorrent password from the wizard/configuration.
- Centered custom dialogs over their parent windows.
- Replaced the temporary-buffer QImage conversion with direct QPixmap file loading.
- Added atomic settings writes and graceful handling of a damaged settings JSON file.
- Added an in-app Settings action that reuses the Setup Wizard to edit TMDB, qBittorrent, and language preferences after installation.
- Added canonical file-path identity and a rescan-time merge for legacy duplicates; poster cache files are migrated to the surviving record.
- Added a build requirements file and explicit error handling to `build.bat`.
- Updated Linux launcher behavior and documentation for current platform support.

## Validation performed in the editing environment

- Python compilation and AST parsing completed successfully.
- SQLite smoke tests passed for title CRUD, bulk import/de-duplication, genres, associations, reviews, foreign-key enforcement, and database integrity.
- A `unittest` suite is included in `tests/` and covers SQLite CRUD, relationships, de-duplication, and foreign-key enforcement. Worker tasks were additionally smoke-tested with mocked HTTP/API responses.

## Validation still required on a desktop machine

The editing environment did not have PyQt5 or `qbittorrent-api` installed, and network access prevented installing them. Therefore the GUI was not launched here. Before publishing this build, run the application on Windows and Linux, test the Setup Wizard, scan a sample folder, TMDB search/poster download, qBittorrent timeout behavior, CSV export, and compile the installer with Inno Setup.

This archive contains source code only. It does not contain `.env`, `.git`, a database with personal data, PyInstaller output, or an installer binary. No commit, push, pull request, or other change was made to the GitHub repository.


### Settings button visibility

The Settings action is placed in the custom title bar next to the window controls. This keeps it visible even when the main toolbar is crowded. It opens the existing Setup Wizard in edit mode.
