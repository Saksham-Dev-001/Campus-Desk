"""Seed official college timetables for Section A (CSE & CS) and Section B (AI & DS)
into both SQLite and PostgreSQL (Supabase).

Preserves all other branches and college data intact.
"""
import os
import sys
import shutil
import sqlite3
import psycopg2
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SQLITE_PATH = "instance/campusdesk.db"
PG_URL = "postgresql://postgres.fcdbupkcvccxublaxbti:Campusdesk%407311@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"

# Image paths
IMG_SEC_A = r"C:\Users\Pravin Sharma\.gemini\antigravity\brain\163b2008-8db2-4ec6-8035-81f6db424879\.user_uploaded\media_1790629715346.jpg"
IMG_SEC_B = r"C:\Users\Pravin Sharma\.gemini\antigravity\brain\163b2008-8db2-4ec6-8035-81f6db424879\.user_uploaded\media_1790629715323.jpg"

# Standard target columns
COURSE_ID = 1  # B.Tech
YEAR_ID = 1    # 1st Year
SEM_ID = 1     # Sem 1

# Subjects:
# 3: Engineering Chemistry
# 145: Engineering Mathematics
# 146: Communication Skills
# 147: Programming for Problem Solving
# 148: Digital Electronics
# 149: Fundamental of Cyber Security & Ethical Hacking
# 150: Engineering Chemistry Lab
# 151: Communication Skills Lab
# 152: Programming for Problem Solving Lab
# 153: Library
# 154: Extra Curricular Activities

# Teachers:
# 5: Dr. Aastha Pareek
# 6: Dr. A. H. Khan
# 7: Dr. Vishal Saxena
# 8: Dr. Pankaj Meel
# 9: Mr. Vikas Singh
# 10: Mr. Happy Dabla
# 11: Dr. Syed Firoz Haider
# 12: Mr. Sikander Khan
# 13: Mr. Toofan Mukharjee
# 14: Mr. Vijay Sharma
# 15: Dr. Nisha Poonia

SECTION_A_SCHEDULE = [
    # MONDAY
    ("Mon", "09:35", "10:30", "SL1", 3, 5, None),
    ("Mon", "10:30", "11:25", "SL1", 145, 6, None),
    ("Mon", "11:25", "12:20", "SL1", 147, 9, None),
    ("Mon", "12:20", "13:10", "Library", 153, None, None),
    ("Mon", "13:45", "15:25", "Chem Lab", 150, 5, "A1"),
    ("Mon", "13:45", "15:25", "Comm Lab", 151, 15, "A2"),

    # TUESDAY
    ("Tue", "09:35", "10:30", "SL1", 148, 10, None),
    ("Tue", "10:30", "11:25", "SL1", 145, 6, None),
    ("Tue", "11:25", "12:20", "SL1", 147, 9, None),
    ("Tue", "12:20", "13:10", "Library", 153, None, None),
    ("Tue", "13:45", "15:25", "Comm Lab", 151, 15, "A1"),
    ("Tue", "13:45", "15:25", "Chem Lab", 150, 5, "A2"),

    # WEDNESDAY
    ("Wed", "09:35", "10:30", "SL1", 3, 5, None),
    ("Wed", "10:30", "11:25", "Library", 153, None, None),
    ("Wed", "11:25", "12:20", "SL1", 149, 12, None),
    ("Wed", "12:20", "13:10", "SL1", 148, 10, None),
    ("Wed", "13:45", "14:35", "SL1", 146, 8, None),
    ("Wed", "14:35", "15:25", "Library", 153, None, None),

    # THURSDAY
    ("Thu", "09:35", "10:30", "SL1", 145, 6, None),
    ("Thu", "10:30", "11:25", "SL1", 3, 5, None),
    ("Thu", "11:25", "12:20", "Library", 153, None, None),
    ("Thu", "12:20", "13:10", "SL1", 149, 12, None),
    ("Thu", "13:45", "14:35", "SL1", 146, 8, None),
    ("Thu", "14:35", "15:25", "SL1", 148, 10, None),

    # FRIDAY
    ("Fri", "09:35", "10:30", "SL1", 145, 6, None),
    ("Fri", "10:30", "11:25", "Library", 153, None, None),
    ("Fri", "11:25", "12:20", "SL1", 3, 5, None),
    ("Fri", "12:20", "13:10", "SL1", 146, 8, None),
    ("Fri", "13:45", "15:25", "Computer Lab", 152, 14, "A1"),
    ("Fri", "13:45", "15:25", "Computer Lab", 152, 12, "A2"),

    # SATURDAY
    ("Sat", "09:35", "10:30", "SL1", 145, 6, None),
    ("Sat", "10:30", "11:25", "SL1", 3, 5, None),
    ("Sat", "11:25", "12:20", "SL1", 147, 9, None),
    ("Sat", "12:20", "13:10", "SL1", 149, 12, None),
    ("Sat", "13:45", "15:25", "Activity Center", 154, None, None),
]

SECTION_B_SCHEDULE = [
    # MONDAY
    ("Mon", "09:35", "10:30", "SL-4", 149, 13, None),
    ("Mon", "10:30", "11:25", "SL-4", 3, 5, None),
    ("Mon", "11:25", "12:20", "Library", 153, None, None),
    ("Mon", "12:20", "13:10", "SL-4", 145, 7, None),
    ("Mon", "13:45", "14:35", "SL-4", 146, 8, None),
    ("Mon", "14:35", "15:25", "Library", 153, None, None),

    # TUESDAY
    ("Tue", "09:35", "10:30", "SL-4", 3, 5, None),
    ("Tue", "10:30", "11:25", "SL-4", 145, 7, None),
    ("Tue", "11:25", "13:10", "Chem Lab", 150, 5, "B1"),
    ("Tue", "11:25", "13:10", "Comm Lab", 151, 15, "B2"),
    ("Tue", "13:45", "14:35", "SL-4", 146, 8, None),
    ("Tue", "14:35", "15:25", "Library", 153, None, None),

    # WEDNESDAY
    ("Wed", "09:35", "10:30", "SL-4", 148, 11, None),
    ("Wed", "10:30", "11:25", "SL-4", 3, 5, None),
    ("Wed", "11:25", "12:20", "SL-4", 147, 9, None),
    ("Wed", "12:20", "13:10", "SL-4", 145, 7, None),
    ("Wed", "13:45", "15:25", "Computer Lab", 152, 14, "B1"),
    ("Wed", "13:45", "15:25", "Computer Lab", 152, 12, "B2"),

    # THURSDAY
    ("Thu", "09:35", "10:30", "SL-4", 149, 13, None),
    ("Thu", "10:30", "11:25", "Library", 153, None, None),
    ("Thu", "11:25", "12:20", "SL-4", 147, 9, None),
    ("Thu", "12:20", "13:10", "SL-4", 148, 11, None),
    ("Thu", "13:45", "14:35", "Library", 153, None, None),
    ("Thu", "14:35", "15:25", "SL-4", 146, 8, None),

    # FRIDAY
    ("Fri", "09:35", "10:30", "SL-4", 148, 11, None),
    ("Fri", "10:30", "11:25", "Library", 153, None, None),
    ("Fri", "11:25", "12:20", "SL-4", 147, 9, None),
    ("Fri", "12:20", "13:10", "SL-4", 3, 5, None),
    ("Fri", "13:45", "15:25", "Comm Lab", 151, 15, "B1"),
    ("Fri", "13:45", "15:25", "Chem Lab", 150, 5, "B2"),

    # SATURDAY
    ("Sat", "09:35", "10:30", "SL-4", 145, 7, None),
    ("Sat", "10:30", "11:25", "SL-4", 149, 13, None),
    ("Sat", "11:25", "12:20", "Library", 153, None, None),
    ("Sat", "12:20", "13:10", "SL-4", 3, 5, None),
    ("Sat", "13:45", "15:25", "Activity Center", 154, None, None),
]

# Branch mappings:
# Branch code -> (branch_id, section_id, {batch_name: batch_id})
BRANCH_CONFIG = {
    # Section A
    "CSE": (1, 1, {"A1": 1, "A2": 53}),
    "CS":  (2, 5, {"A1": 13, "A2": 63}),
    # Section B
    "AI":  (10, 22, {"B1": 106, "B2": 107}),
    "DS":  (11, 24, {"B1": 108, "B2": 109}),
}

def build_entries():
    all_rows = []
    # Section A branches: CSE and CS
    for br_code in ["CSE", "CS"]:
        b_id, s_id, batch_map = BRANCH_CONFIG[br_code]
        for day, start, end, room, sub_id, tch_id, batch_str in SECTION_A_SCHEDULE:
            bt_id = batch_map.get(batch_str) if batch_str else None
            all_rows.append({
                "day": day,
                "start_time": start,
                "end_time": end,
                "room": room,
                "teacher_id": tch_id,
                "course_id": COURSE_ID,
                "branch_id": b_id,
                "year_id": YEAR_ID,
                "semester_id": SEM_ID,
                "section_id": s_id,
                "batch_id": bt_id,
                "subject_id": sub_id,
            })

    # Section B branches: AI and DS
    for br_code in ["AI", "DS"]:
        b_id, s_id, batch_map = BRANCH_CONFIG[br_code]
        for day, start, end, room, sub_id, tch_id, batch_str in SECTION_B_SCHEDULE:
            bt_id = batch_map.get(batch_str) if batch_str else None
            all_rows.append({
                "day": day,
                "start_time": start,
                "end_time": end,
                "room": room,
                "teacher_id": tch_id,
                "course_id": COURSE_ID,
                "branch_id": b_id,
                "year_id": YEAR_ID,
                "semester_id": SEM_ID,
                "section_id": s_id,
                "batch_id": bt_id,
                "subject_id": sub_id,
            })
    return all_rows

def seed_sqlite(entries):
    print("--- Seeding SQLite ---")
    conn = sqlite3.connect(SQLITE_PATH)
    cur = conn.cursor()

    # 1. Clean existing Section A & B entries + rogue entries
    cur.execute("""
        DELETE FROM timetable 
        WHERE branch_id IN (1, 2, 10, 11) 
           OR section_id IS NULL 
           OR id IN (281, 282)
    """)
    deleted = cur.rowcount
    print(f"Deleted {deleted} old/rogue entries in SQLite.")

    # 2. Insert new entries
    insert_sql = """
        INSERT INTO timetable (day, start_time, end_time, room, teacher_id, 
                               course_id, branch_id, year_id, semester_id, 
                               section_id, batch_id, subject_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for e in entries:
        cur.execute(insert_sql, (
            e["day"], e["start_time"], e["end_time"], e["room"], e["teacher_id"],
            e["course_id"], e["branch_id"], e["year_id"], e["semester_id"],
            e["section_id"], e["batch_id"], e["subject_id"]
        ))
    print(f"Inserted {len(entries)} entries into SQLite timetable.")

    # 3. Update student Aryan Shah (AI) to Section B (22), Batch B1 (106)
    cur.execute("UPDATE students SET section_id = 22, batch_id = 106 WHERE enrollment_number = 'AI2024001'")
    print(f"Updated Aryan Shah in SQLite: {cur.rowcount} row(s).")

    conn.commit()
    conn.close()
    print("SQLite seeding completed successfully.")

def seed_postgres(entries):
    print("\n--- Seeding PostgreSQL (Supabase) ---")
    conn = psycopg2.connect(PG_URL)
    cur = conn.cursor()

    # 1. Clean existing Section A & B entries + rogue entries
    cur.execute("""
        DELETE FROM timetable 
        WHERE branch_id IN (1, 2, 10, 11) 
           OR section_id IS NULL 
           OR id IN (281, 282)
    """)
    deleted = cur.rowcount
    print(f"Deleted {deleted} old/rogue entries in PostgreSQL.")

    # 2. Insert new entries
    insert_sql = """
        INSERT INTO timetable (day, start_time, end_time, room, teacher_id, 
                               course_id, branch_id, year_id, semester_id, 
                               section_id, batch_id, subject_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    for e in entries:
        cur.execute(insert_sql, (
            e["day"], e["start_time"], e["end_time"], e["room"], e["teacher_id"],
            e["course_id"], e["branch_id"], e["year_id"], e["semester_id"],
            e["section_id"], e["batch_id"], e["subject_id"]
        ))
    print(f"Inserted {len(entries)} entries into PostgreSQL timetable.")

    # 3. Update student Aryan Shah (AI) to Section B (22), Batch B1 (106)
    cur.execute("UPDATE students SET section_id = 22, batch_id = 106 WHERE enrollment_number = 'AI2024001'")
    print(f"Updated Aryan Shah in PostgreSQL: {cur.rowcount} row(s).")

    # 4. Sync PostgreSQL sequence
    cur.execute("SELECT setval('timetable_id_seq', (SELECT COALESCE(MAX(id), 1) FROM timetable));")
    print("PostgreSQL sequence 'timetable_id_seq' updated.")

    conn.commit()
    conn.close()
    print("PostgreSQL seeding completed successfully.")

def seed_official_files():
    print("\n--- Registering Official Timetable Image Files ---")
    from app import create_app
    from models import db, FileRecord, User
    from services.storage import get_storage_provider

    app = create_app()
    with app.app_context():
        provider = get_storage_provider(app.config)
        admin = User.query.filter_by(role="admin").first()
        admin_id = admin.id if admin else 1

        docs_to_register = [
            ("Official Timetable - Section A (CSE & CS).jpg", IMG_SEC_A),
            ("Official Timetable - Section B (AI & DS).jpg", IMG_SEC_B),
        ]

        for display_name, img_path in docs_to_register:
            if not os.path.exists(img_path):
                print(f"Image not found at {img_path}")
                continue

            with open(img_path, "rb") as f:
                data = f.read()

            size = len(data)
            storage_ref = provider.upload_file(data, display_name, folder_path="_timetable")
            print(f"Uploaded {display_name} via {provider.name} -> ref: {storage_ref}")

            # Check if record already exists in FileRecord
            existing = FileRecord.query.filter_by(filename=display_name).first()
            if existing:
                existing.storage_provider = provider.name
                existing.storage_ref = storage_ref
                existing.size_bytes = size
                existing.status = "active"
                existing.mime_type = "image/jpeg"
                existing.course_id = 1
                existing.year_id = 1
                existing.semester_id = 1
                existing.branch_id = None
                existing.section_id = None
                existing.batch_id = None
            else:
                fr = FileRecord(
                    filename=display_name,
                    original_filename=display_name,
                    mime_type="image/jpeg",
                    size_bytes=size,
                    storage_provider=provider.name,
                    storage_ref=storage_ref,
                    uploaded_by=admin_id,
                    status="active",
                    course_id=1,
                    year_id=1,
                    semester_id=1,
                    branch_id=None,
                    section_id=None,
                    batch_id=None
                )
                db.session.add(fr)

        db.session.commit()
        print("Official Timetable documents committed to local DB.")

        # Also replicate the FileRecord rows into PostgreSQL so Supabase has them
        # Connect to both DBs and copy files table rows for Official Timetable
        s_conn = sqlite3.connect(SQLITE_PATH)
        p_conn = psycopg2.connect(PG_URL)
        s_cur = s_conn.cursor()
        p_cur = p_conn.cursor()

        s_cur.execute("SELECT id, filename, original_filename, mime_type, size_bytes, folder_id, version, status, storage_provider, storage_ref, uploaded_by, uploaded_at, updated_at, course_id, branch_id, year_id, semester_id, section_id, batch_id, subject_id FROM files WHERE filename LIKE 'Official Timetable%'")
        rows = s_cur.fetchall()
        for r in rows:
            p_cur.execute("""
                INSERT INTO files (id, filename, original_filename, mime_type, size_bytes, folder_id, version, status, storage_provider, storage_ref, uploaded_by, uploaded_at, updated_at, course_id, branch_id, year_id, semester_id, section_id, batch_id, subject_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    storage_provider = EXCLUDED.storage_provider,
                    storage_ref = EXCLUDED.storage_ref,
                    status = 'active',
                    version = EXCLUDED.version,
                    size_bytes = EXCLUDED.size_bytes;
            """, r)
            print(f"Synced {r[1]} (id={r[0]}) to PostgreSQL files table.")

        p_cur.execute("SELECT setval('files_id_seq', (SELECT COALESCE(MAX(id), 1) FROM files));")
        p_conn.commit()
        s_conn.close()
        p_conn.close()
        print("Official Timetable documents synced to PostgreSQL successfully.")

if __name__ == "__main__":
    entries = build_entries()
    print(f"Built total {len(entries)} timetable entries ({len(entries)//4} per branch).")
    seed_sqlite(entries)
    seed_postgres(entries)
    seed_official_files()
    print("\nALL TIMETABLE TASKS COMPLETED!")
