# CampusDesk — Fix Pack v1

Fixes: `BuildError: Could not build url for endpoint 'file_preview'`

## What was wrong

The preview route was defined inside the `api` blueprint (URL prefix `/api`),
so its endpoint name is `api.file_preview`, not `file_preview`.

`timetable.html` was calling `url_for('file_preview', ...)` — wrong name.

## What this pack does

1. **timetable.html** — corrected to use `url_for('api.file_preview', ...)`
2. **app.py** — adds an ALIAS endpoint so `url_for('file_preview')` ALSO works
   (future-proof — both names valid)

## Apply

1. Copy `templates/timetable.html` → your project (overwrite)
2. Copy `app.py` → your project (overwrite)
3. Restart: `start.bat`

## Done

Timetable → "Official Timetable" tab → PDF/image should now embed correctly.
No DB reset needed.
