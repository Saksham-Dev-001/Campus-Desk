"""Database migration: create teacher_subjects table, populate folder.subject_id, and assign subjects."""
import sqlite3

def run():
    con = sqlite3.connect("instance/campusdesk.db")
    cur = con.cursor()

    # 1. Create table
    print("1. Creating teacher_subjects table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS teacher_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        subject_id INTEGER NOT NULL REFERENCES subjects(id),
        UNIQUE(user_id, subject_id)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_teacher_subjects_user_id ON teacher_subjects(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_teacher_subjects_subject_id ON teacher_subjects(subject_id);")
    con.commit()

    # 2. Match folders to subjects
    print("2. Matching folders to subjects...")
    subjects = cur.execute("SELECT id, code, name FROM subjects").fetchall()
    folders = cur.execute("SELECT id, name, parent_id, subject_id FROM folders").fetchall()

    folder_sub_map = {}
    updated_folders = 0

    # Common folder names that should NEVER be mapped to a subject
    ignore_names = {
        "notes", "lab manuals & practical records", "previous year question papers (pyqs)",
        "section a", "section b", "a1", "a2", "a3", "1st year", "2nd year", "3rd year", "4th year",
        "sem 1 - notes & material", "sem 2 - notes & material", "sem 3 - notes & material",
        "sem 4 - notes & material", "sem 5 - notes & material", "sem 6 - notes & material",
        "sem 7 - notes & material", "sem 8 - notes & material"
    }

    for fid, fname, pid, subid in folders:
        fn_clean = fname.strip().lower()
        if fn_clean in ignore_names:
            continue

        matched_sid = None
        # Match by code
        for sid, scode, sname in subjects:
            if scode and scode.lower() in fn_clean:
                matched_sid = sid
                break
        # Match by exact name
        if not matched_sid:
            for sid, scode, sname in subjects:
                if sname.strip().lower() == fn_clean:
                    matched_sid = sid
                    break

        if matched_sid:
            folder_sub_map[fid] = matched_sid
            cur.execute("UPDATE folders SET subject_id = ? WHERE id = ?", (matched_sid, fid))
            updated_folders += 1

    # Propagate subject_id to child folders (e.g. Notes inside 1FY1-05 Communication Skills)
    for fid, fname, pid, subid in folders:
        if fid not in folder_sub_map and pid in folder_sub_map:
            p_sub = folder_sub_map[pid]
            folder_sub_map[fid] = p_sub
            cur.execute("UPDATE folders SET subject_id = ? WHERE id = ?", (p_sub, fid))
            updated_folders += 1

    con.commit()
    print(f"Updated {updated_folders} folders with subject_id.")

    # 3. Assign subjects to teachers
    print("3. Seeding teacher_subjects...")
    # Map teacher username -> list of subject codes
    teacher_assignments = {
        "aastha": ["1FY2-03", "1FY2-23"],
        "pankaj": ["1FY1-05", "1FY1-25"],
        "ahkhan": ["1FY2-01", "MA102"],
        "vishal": ["1FY2-01", "MA102"],
        "vikas": ["1FY3-06", "CS102"],
        "happy": ["1FY3-07"],
        "firoz": ["1FY3-07"],
        "sikander": ["1FY3-08", "1FY3-26"],
        "toofan": ["1FY3-08"],
        "vijay": ["1FY3-06", "1FY3-26"],
        "nisha": ["1FY1-05", "1FY1-25"],
    }

    assigned_count = 0
    for uname, codes in teacher_assignments.items():
        user = cur.execute("SELECT id, name FROM users WHERE username = ?", (uname,)).fetchone()
        if not user:
            print(f"User {uname} not found, skipping.")
            continue
        uid, uname_full = user

        for code in codes:
            # Find all subject rows for this code
            sub_rows = cur.execute("SELECT id, name FROM subjects WHERE code = ?", (code,)).fetchall()
            for sid, sname in sub_rows:
                cur.execute("""
                INSERT OR IGNORE INTO teacher_subjects (user_id, subject_id)
                VALUES (?, ?)
                """, (uid, sid))
                assigned_count += 1
        print(f"Assigned {len(codes)} subject codes to {uname_full} ({uname})")

    con.commit()
    print(f"Total teacher_subject assignments inserted: {assigned_count}")

    # Summary
    print("\n--- Verification Summary ---")
    for row in cur.execute("""
    SELECT u.username, u.name, count(ts.id), group_concat(DISTINCT s.code)
    FROM users u
    JOIN teacher_subjects ts ON u.id = ts.user_id
    JOIN subjects s ON ts.subject_id = s.id
    GROUP BY u.id
    ORDER BY u.name
    """).fetchall():
        print(row)

    con.close()

if __name__ == "__main__":
    run()
