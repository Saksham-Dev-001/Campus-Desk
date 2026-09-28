import sys
from pathlib import Path
# Ensure project root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

"""CampusDesk — database diagnostic. Run after reset to confirm data exists."""
from app import app
from models import (db, User, Student, Teacher, Course, Branch, Year, Semester,
                    Section, Batch, Subject, Notice, Assignment, TimetableEntry,
                    Folder)

with app.app_context():
    print("")
    print("=" * 60)
    print("  CampusDesk — Database Verification")
    print("=" * 60)

    def c(label, q):
        try:
            n = q.count()
        except Exception as e:
            n = f"ERROR ({e})"
        print(f"  {label:<22} {n}")

    c("Courses", Course.query)
    c("Branches", Branch.query)
    c("Years", Year.query)
    c("Semesters", Semester.query)
    c("Sections", Section.query)
    c("Batches", Batch.query)
    c("Subjects", Subject.query)
    c("Users", User.query)
    c("Students", Student.query)
    c("Teachers", Teacher.query)
    c("Folders", Folder.query)
    c("Notices", Notice.query)
    c("Assignments", Assignment.query)
    c("Timetable", TimetableEntry.query)

    print("")
    print("  --- Students per branch ---")
    for b in Branch.query.order_by(Branch.code).all():
        n = Student.query.filter_by(branch_id=b.id).count()
        if n:
            print(f"    {b.code:<10} {n}")

    print("")
    print("  --- Demo logins ---")
    for u in ["admin", "teacher1", "teacher2", "CSE2024001",
              "CSE2024003", "CS2024001", "IT2024001"]:
        user = User.query.filter_by(username=u).first()
        if user:
            extra = f"  [{user.student.academic_label}]" if user.student else ""
            print(f"    [OK] {u:<12} {user.name}{extra}")
        else:
            print(f"    [XX] {u:<12} NOT FOUND")

    print("")
    print("=" * 60)
    print("  If all counts > 0, data is good. Now run start.bat.")
    print("=" * 60)
    print("")
