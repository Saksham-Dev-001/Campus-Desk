import sys
from pathlib import Path
# Ensure project root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

"""CampusDesk — Reset database: drop all tables, recreate, reseed.

    python reset.py

WARNING: deletes the entire database and all uploaded files.
"""
import shutil
import sys
from pathlib import Path

from app import app
from models import db
from config import Config

def _wipe_uploads():
    up = Path(Config.UPLOAD_FOLDER)
    if up.exists():
        try:
            shutil.rmtree(up, ignore_errors=True)
            print(f"  [OK] Removed uploads: {up}")
        except Exception as e:
            print(f"  [WARN] Could not remove uploads: {e}")
    else:
        print("  [OK] No uploads folder to remove.")

if __name__ == "__main__":
    print("")
    print("=" * 60)
    print("  CampusDesk — Database Reset")
    print("=" * 60)
    print("")

    print("[1/3] Wiping uploads...")
    _wipe_uploads()

    print("[2/3] Dropping and recreating tables...")
    with app.app_context():
        Path(Config.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
        db.drop_all()
        db.create_all()
        print("  [OK] Tables recreated.")

        print("[3/3] Seeding fresh college data...")
        try:
            try:
                from scripts.seed import seed_all
            except ImportError:
                from seed import seed_all
            seed_all()
            print("  [OK] Seed successful.")
        except Exception:
            import traceback
            print("")
            print("  [ERROR] Seed failed:")
            traceback.print_exc()
            sys.exit(1)

    print("")
    print("=" * 60)
    print("  Reset complete. Now run: python verify.py")
    print("=" * 60)
    print("")
