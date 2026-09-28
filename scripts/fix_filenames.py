import sys
from pathlib import Path
# Ensure project root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# CampusDesk - One-time fix: append missing extensions to existing files.
# Run:  python fix_filenames.py
from app import app
from config import Config
from models import db, FileRecord

with app.app_context():
    allowed = Config.ALLOWED_EXTENSIONS
    fixed = 0
    checked = 0

    for rec in FileRecord.query.all():
        checked += 1
        name = (rec.filename or "").strip()
        orig = (rec.original_filename or "").strip()

        if "." in name:
            continue
        if "." not in orig:
            continue

        ext = orig.rsplit(".", 1)[1].lower()
        if ext not in allowed:
            continue

        new_name = "{}.{}".format(name, ext)
        print("  [FIX] {}  ->  {}".format(name, new_name))
        rec.filename = new_name
        fixed += 1

    if fixed:
        db.session.commit()

    print("")
    print("=" * 60)
    print("  Checked {} file(s). Fixed {} filename(s).".format(checked, fixed))
    print("=" * 60)
    print("")
