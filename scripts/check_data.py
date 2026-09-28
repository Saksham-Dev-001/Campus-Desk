import sys
from pathlib import Path
# Ensure project root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# CampusDesk - Check if database has the expected seed data.
# Run:  python check_data.py
from app import app
from models import db, Course, Branch, Year, Semester, Section, Batch, User, Student

with app.app_context():
    print("")
    print("=" * 60)
    print("  CampusDesk - Data Check")
    print("=" * 60)

    counts = {
        "Courses":   Course.query.count(),
        "Branches":  Branch.query.count(),
        "Years":     Year.query.count(),
        "Semesters": Semester.query.count(),
        "Sections":  Section.query.count(),
        "Batches":   Batch.query.count(),
        "Users":     User.query.count(),
        "Students":  Student.query.count(),
    }
    for k, v in counts.items():
        flag = "OK " if v > 0 else "!! "
        print("  [{}] {:<12} {}".format(flag, k, v))

    print("")
    print("  --- First 5 branches ---")
    branches = Branch.query.order_by(Branch.code).limit(5).all()
    if branches:
        for b in branches:
            print("     id={:<3} code={:<8} name={}".format(b.id, b.code, b.name))
    else:
        print("     (no branches)")

    print("")
    print("  --- First 5 courses ---")
    courses = Course.query.order_by(Course.name).limit(5).all()
    if courses:
        for c in courses:
            print("     id={:<3} name={}".format(c.id, c.name))
    else:
        print("     (no courses)")

    print("")
    if counts["Branches"] == 0 or counts["Courses"] == 0:
        print("  !! Database has no courses/branches.")
        print("     Run:  python reset.py")
    else:
        print("  Data OK. If dropdowns are still empty, it's a JS/API issue.")
        print("  Open browser DevTools (F12) -> Network -> reload the page,")
        print("  then look for the /api/branches request and its response.")
    print("=" * 60)
    print("")
