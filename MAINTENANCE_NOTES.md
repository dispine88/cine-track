# Maintenance notes

Baseline: `feature/raw-sql` commit `37d494a` (`refactor: added tests & fixed bugs`). Changes in this folder are local working-copy updates only.

## Current build

- Settings is a compact editor for TMDB and qBittorrent; the first-run Setup Wizard remains separate.
- SQLite connections enable foreign keys and an 8-second busy timeout, use WAL, and always close.
- File-path deduplication begins with `BEGIN IMMEDIATE` so simultaneous importers cannot pass the duplicate check together.
- Nullable title and review fields can be explicitly cleared by passing `None`; omitted arguments remain unchanged.
- Sample seed data fills missing entries and is safe to run more than once.
- `PRAGMA user_version` records the initial schema version. Future schema changes need explicit migration functions.
- Worker failures are recorded to `cinetrack.log` using exception types and traceback frames only; raw exception messages are omitted to avoid logging credential-bearing request URLs.
- Explicitly clearing the TMDB key sets a preference that suppresses the source-only `.env` fallback, so a removed key does not silently reappear.
- qBittorrent and TMDB operations run off the UI thread with network timeouts.

## Validation

Run `python -m compileall -q main.py config.py gui database tests` and `python -m unittest discover -s tests -v` before building. The build script checks only project modules and tests, not the local virtual environment.

The 18-test suite covers SQLite CRUD, duplicate imports, concurrent duplicate insertion, metadata clearing, partial/idempotent seeding, relationships, foreign-key enforcement, schema versioning, CSV encoding, TMDB response validation, and worker helpers.

A Windows GUI smoke test is still required for the actual PyQt window, TMDB, qBittorrent, and installed application. Build with `build.bat`, then run `build_setup.bat` (or compile `installer.iss` in Inno Setup). The Linux editing environment cannot produce a genuine Windows installer.
