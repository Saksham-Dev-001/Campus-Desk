import sys
from pathlib import Path
# Ensure project root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# CampusDesk - Schema migration (additive only)
# Adds any missing columns from models.py to existing SQLite tables.
# Does NOT drop or modify existing data.
#
# Usage:  python migrate.py
from sqlalchemy import inspect, text
from app import app
from models import db

def migrate():
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    changes = 0

    for table_name, table in db.metadata.tables.items():
        if table_name not in existing_tables:
            continue

        current_cols = {c["name"] for c in inspector.get_columns(table_name)}

        for col in table.columns:
            if col.name in current_cols:
                continue

            col_type = col.type.compile(dialect=db.engine.dialect)
            sql = "ALTER TABLE {} ADD COLUMN {} {}".format(
                table_name, col.name, col_type
            )
            print("  + {}.{}  ({})".format(table_name, col.name, col_type))
            try:
                db.session.execute(text(sql))
                db.session.commit()
                changes += 1
            except Exception as e:
                db.session.rollback()
                print("    [SKIP] {}".format(e))

    return changes

if __name__ == "__main__":
    print("")
    print("=" * 64)
    print("  CampusDesk - Schema Migration (additive only)")
    print("=" * 64)
    print("")
    print("[1/2] Creating any brand-new tables...")
    with app.app_context():
        db.create_all()
        print("      [OK] create_all() done.")

        print("[2/2] Adding missing columns to existing tables...")
        n = migrate()

    print("")
    if n == 0:
        print("  [OK] Schema already up to date. No changes needed.")
    else:
        print("  [OK] Applied {} column change(s).".format(n))
    print("  Now restart the server:  start.bat")
    print("=")
