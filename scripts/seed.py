import sys
from pathlib import Path
# Ensure project root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

"""Seed realistic college-wide demo data for CampusDesk."""
from datetime import datetime, timedelta
from models import (db, User, Student, Teacher, Course, Branch, Year, Semester,
                    Section, Batch, Subject, Notice, Assignment, TimetableEntry,
                    Folder, StudentRequest, TeacherBranch)

DEMO_PASSWORD = "password123"

COURSES = ["B.Tech", "M.Tech", "BCA", "MCA", "Diploma"]

# FIX: 'CS' branch was missing from B.Tech. Now added.
BRANCH_DEFS = {
    "B.Tech": [
        ("Computer Science & Engineering", "CSE"),
        ("Computer Science",               "CS"),
        ("Information Technology",         "IT"),
        ("Electronics & Communication Engineering", "ECE"),
        ("Electrical & Electronics Engineering",    "EEE"),
        ("Mechanical Engineering",         "ME"),
        ("Civil Engineering",              "CE"),
        ("Artificial Intelligence & Machine Learning", "AIML"),
        ("Data Science",                   "DS"),
    ],
    "M.Tech": [
        ("Computer Science & Engineering", "MT-CSE"),
        ("Electronics & Communication Engineering", "MT-ECE"),
    ],
    "BCA": [("Bachelor of Computer Applications", "BCA")],
    "MCA": [("Master of Computer Applications", "MCA")],
    "Diploma": [
        ("Diploma in Computer Engineering", "D-CSE"),
        ("Diploma in Mechanical Engineering", "D-ME"),
    ],
}

YEAR_DEFS = [("1st Year", 1), ("2nd Year", 2), ("3rd Year", 3), ("4th Year", 4)]
SEM_DEFS = [(f"Sem {i}", i) for i in range(1, 9)]

# Which (branch, year) combos get sections/batches built
SECTION_MATRIX = {
    "CSE":  ["1st Year", "2nd Year"],
    "CS":   ["1st Year"],
    "IT":   ["1st Year"],
    "ECE":  ["1st Year"],
    "EEE":  ["1st Year"],
    "ME":   ["1st Year"],
    "CE":   ["1st Year"],
    "AIML": ["1st Year"],
    "DS":   ["1st Year"],
}
SECTIONS = ["A", "B"]
BATCHES = ["A1", "A2", "A3"]

SUBJECTS = {
    "COMMON_SEM1": [
        ("Engineering Mathematics I", "MA101"),
        ("Engineering Physics", "PH101"),
        ("Engineering Chemistry", "CH101"),
        ("Basic Electrical Engineering", "EE101"),
        ("Programming Fundamentals", "CS101"),
    ],
    "COMMON_SEM2": [
        ("Engineering Mathematics II", "MA102"),
        ("Applied Physics", "PH102"),
        ("Environmental Studies", "EV102"),
        ("Object-Oriented Programming", "CS102"),
        ("Engineering Mechanics", "ME102"),
    ],
    "CSE_SEM3": [
        ("Data Structures", "CS201"),
        ("Discrete Mathematics", "MA201"),
        ("Digital Logic Design", "EC201"),
        ("Object-Oriented Programming with Java", "CS202"),
        ("Computer Organization & Architecture", "CS203"),
    ],
    "CSE_SEM4": [
        ("Design & Analysis of Algorithms", "CS204"),
        ("Operating Systems", "CS205"),
        ("Database Management Systems", "CS206"),
        ("Computer Networks", "CS207"),
    ],
    "CSE_SEM5": [
        ("Theory of Computation", "CS301"),
        ("Software Engineering", "CS302"),
        ("Web Technologies", "CS303"),
        ("Computer Graphics", "CS304"),
    ],
    "CSE_SEM6": [
        ("Compiler Design", "CS305"),
        ("Artificial Intelligence", "CS306"),
        ("Mobile Application Development", "CS307"),
        ("Cryptography & Network Security", "CS308"),
    ],
    "CSE_SEM7": [
        ("Machine Learning", "CS401"),
        ("Cloud Computing", "CS402"),
        ("Big Data Analytics", "CS403"),
        ("Internet of Things", "CS404"),
    ],
    "CSE_SEM8": [
        ("Major Project", "CS499"),
        ("Industrial Internship", "CS498"),
        ("Blockchain Technology", "CS405"),
    ],
}

STUDENT_DEFS = [
    ("Rahul Sharma",   "CSE2024003",  "CSE",  "1st Year", "A", "A1", "student"),
    ("Priya Nair",     "CSE2024004",  "CSE",  "1st Year", "A", "A1", "student"),
    ("Rohit Verma",    "CSE2024005",  "CSE",  "1st Year", "A", "A1", "student"),
    ("Vishal Kumar",   "CSE2024001",  "CSE",  "1st Year", "A", "A2", "student_admin"),
    ("Saksham Singh",  "CSE2024002",  "CSE",  "1st Year", "A", "A2", "student"),
    ("Neha Gupta",     "CSE2024006",  "CSE",  "1st Year", "A", "A2", "student"),
    ("Karan Singh",    "CSE2024007",  "CSE",  "1st Year", "A", "A3", "student"),
    ("Aditi Sharma",   "CSE2024008",  "CSE",  "1st Year", "B", "A1", "student"),
    ("Devansh Rao",    "CSE2023001",  "CSE",  "2nd Year", "A", "A1", "student"),
    ("Ishita Bose",    "CSE2023002",  "CSE",  "2nd Year", "A", "A1", "student"),
    ("Rahul Sharma",   "CS2024001",   "CS",   "1st Year", "A", "A2", "student"),
    ("Ananya Iyer",    "CS2024002",   "CS",   "1st Year", "A", "A2", "student"),
    ("Vikram Joshi",   "IT2024001",   "IT",   "1st Year", "A", "A1", "student"),
    ("Pooja Reddy",    "ECE2024001",  "ECE",  "1st Year", "A", "A1", "student"),
    ("Manish Kumar",   "ECE2024002",  "ECE",  "1st Year", "A", "A2", "student"),
    ("Sneha Patel",    "EEE2024001",  "EEE",  "1st Year", "A", "A1", "student"),
    ("Arjun Mehta",    "ME2024001",   "ME",   "1st Year", "A", "A1", "student"),
    ("Kavya Rao",      "CE2024001",   "CE",   "1st Year", "A", "A1", "student"),
    ("Aryan Shah",     "AIML2024001", "AIML", "1st Year", "A", "A1", "student"),
    ("Riya Kapoor",    "DS2024001",   "DS",   "1st Year", "A", "A1", "student"),
]

def _u(username, role, name):
    u = User.query.filter_by(username=username).first()
    if u:
        return u
    u = User(username=username, role=role, name=name)
    u.set_password(DEMO_PASSWORD)
    db.session.add(u)
    db.session.flush()
    return u

def seed_all():
    # ---------------- Courses ----------------
    courses = {}
    for cname in COURSES:
        c = Course.query.filter_by(name=cname).first()
        if not c:
            c = Course(name=cname)
            db.session.add(c)
            db.session.flush()
        courses[cname] = c

    # ---------------- Branches ----------------
    branches = {}
    for cname, blist in BRANCH_DEFS.items():
        for bname, bcode in blist:
            b = Branch.query.filter_by(code=bcode).first()
            if not b:
                b = Branch(name=bname, code=bcode, course_id=courses[cname].id)
                db.session.add(b)
                db.session.flush()
            branches[bcode] = b

    # ---------------- Years ----------------
    years = {}
    for yname, idx in YEAR_DEFS:
        y = Year.query.filter_by(name=yname).first()
        if not y:
            y = Year(name=yname, order_index=idx)
            db.session.add(y)
            db.session.flush()
        years[yname] = y

    # ---------------- Semesters ----------------
    sems = {}
    for sname, idx in SEM_DEFS:
        s = Semester.query.filter_by(name=sname).first()
        if not s:
            s = Semester(name=sname, order_index=idx)
            db.session.add(s)
            db.session.flush()
        sems[sname] = s

    # ---------------- Sections & Batches ----------------
    sections_by_key = {}
    batches_by_key = {}
    for bcode, year_list in SECTION_MATRIX.items():
        branch = branches[bcode]
        for yname in year_list:
            y = years[yname]
            for sec_name in SECTIONS:
                sec = Section.query.filter_by(name=sec_name, branch_id=branch.id,
                                              year_id=y.id).first()
                if not sec:
                    sec = Section(name=sec_name, branch_id=branch.id, year_id=y.id)
                    db.session.add(sec)
                    db.session.flush()
                sections_by_key[(bcode, yname, sec_name)] = sec
                for bt_name in BATCHES:
                    bt = Batch.query.filter_by(name=bt_name, section_id=sec.id).first()
                    if not bt:
                        bt = Batch(name=bt_name, section_id=sec.id)
                        db.session.add(bt)
                        db.session.flush()
                    batches_by_key[(bcode, yname, sec_name, bt_name)] = bt

    # ---------------- Subjects ----------------
    def _subject(name, code, branch_code, sem_name):
        branch = branches.get(branch_code)
        if not branch:
            return None
        s = sems[sem_name]
        sub = Subject.query.filter_by(name=name, branch_id=branch.id,
                                      semester_id=s.id).first()
        if not sub:
            sub = Subject(name=name, code=code, branch_id=branch.id, semester_id=s.id)
            db.session.add(sub)
            db.session.flush()
        return sub

    for key, sem_name in (("COMMON_SEM1", "Sem 1"), ("COMMON_SEM2", "Sem 2")):
        for _, bcode in BRANCH_DEFS["B.Tech"]:
            for sname, scode in SUBJECTS[key]:
                _subject(sname, scode, bcode, sem_name)

    for key in ("CSE_SEM3", "CSE_SEM4", "CSE_SEM5", "CSE_SEM6", "CSE_SEM7", "CSE_SEM8"):
        sem_name = f"Sem {key[-1]}"
        for sname, scode in SUBJECTS[key]:
            _subject(sname, scode, "CSE", sem_name)

    prog = Subject.query.filter_by(name="Programming Fundamentals",
                                   branch_id=branches["CSE"].id,
                                   semester_id=sems["Sem 1"].id).first()
    math = Subject.query.filter_by(name="Engineering Mathematics I",
                                   branch_id=branches["CSE"].id,
                                   semester_id=sems["Sem 1"].id).first()
    phy = Subject.query.filter_by(name="Engineering Physics",
                                  branch_id=branches["CSE"].id,
                                  semester_id=sems["Sem 1"].id).first()
    dsa = Subject.query.filter_by(name="Data Structures",
                                  branch_id=branches["CSE"].id,
                                  semester_id=sems["Sem 3"].id).first()

    # ---------------- Users: admin + teachers ----------------
    admin_u = _u("admin", "admin", "System Administrator")
    t1 = _u("teacher1", "teacher", "Dr. Anjali Verma")
    t2 = _u("teacher2", "teacher", "Prof. Rajesh Kumar")

    if not Teacher.query.filter_by(user_id=t1.id).first():
        db.session.add(Teacher(user_id=t1.id, teacher_id="TCH001", department="CSE"))
    if not Teacher.query.filter_by(user_id=t2.id).first():
        db.session.add(Teacher(user_id=t2.id, teacher_id="TCH002", department="CSE"))
    db.session.flush()
    teacher1 = Teacher.query.filter_by(user_id=t1.id).first()
    teacher2 = Teacher.query.filter_by(user_id=t2.id).first()

    # ---------------- Demo branch access ----------------
    # teacher1 → CSE, IT   (non-global)
    # teacher2 → CS, AIML, DS   (non-global)
    for code in ("CSE", "IT"):
        b = branches.get(code)
        if b and not TeacherBranch.query.filter_by(user_id=t1.id, branch_id=b.id).first():
            db.session.add(TeacherBranch(user_id=t1.id, branch_id=b.id))
    for code in ("CS", "AIML", "DS"):
        b = branches.get(code)
        if b and not TeacherBranch.query.filter_by(user_id=t2.id, branch_id=b.id).first():
            db.session.add(TeacherBranch(user_id=t2.id, branch_id=b.id))
    if teacher1:
        teacher1.is_global = False
    if teacher2:
        teacher2.is_global = False
    db.session.flush()

    # ---------------- Students ----------------
    def _student(name, enroll, branch_code, year_name, sec_name, batch_name, role):
        u = User.query.filter_by(username=enroll).first()
        if not u:
            u = User(username=enroll, role=role, name=name)
            u.set_password(DEMO_PASSWORD)
            db.session.add(u)
            db.session.flush()
        s = Student.query.filter_by(enrollment_number=enroll).first()
        if not s:
            s = Student(user_id=u.id, enrollment_number=enroll)
            db.session.add(s)
        branch = branches[branch_code]
        s.course_id = branch.course_id
        s.branch_id = branch.id
        s.year_id = years[year_name].id
        sem_map = {"1st Year": "Sem 1", "2nd Year": "Sem 3",
                   "3rd Year": "Sem 5", "4th Year": "Sem 7"}
        s.semester_id = sems[sem_map[year_name]].id
        s.section_id = sections_by_key[(branch_code, year_name, sec_name)].id
        s.batch_id = batches_by_key[(branch_code, year_name, sec_name, batch_name)].id
        db.session.flush()
        return s

    vishal = None
    for name, enroll, bcode, yname, sec, batch, role in STUDENT_DEFS:
        st = _student(name, enroll, bcode, yname, sec, batch, role)
        if enroll == "CSE2024001":
            vishal = st

    # ---------------- Folders (study material tree) ----------------
    def _folder(name, parent, **targets):
        f = Folder.query.filter_by(name=name,
                                   parent_id=parent.id if parent else None).first()
        if not f:
            f = Folder(name=name, parent_id=parent.id if parent else None,
                       created_by=admin_u.id, **targets)
            db.session.add(f)
            db.session.flush()
        return f

    btech_id = courses["B.Tech"].id

    def _branch_tree(bcode, display):
        b = branches[bcode]
        root = _folder(display, None, course_id=btech_id, branch_id=b.id)
        for yname in SECTION_MATRIX.get(bcode, []):
            y = years[yname]
            sem_name = {"1st Year": "Sem 1", "2nd Year": "Sem 3",
                        "3rd Year": "Sem 5", "4th Year": "Sem 7"}[yname]
            yf = _folder(yname, root, course_id=btech_id, branch_id=b.id, year_id=y.id)
            sf = _folder(sem_name, yf, course_id=btech_id, branch_id=b.id,
                         year_id=y.id, semester_id=sems[sem_name].id)
            for sec_name in SECTIONS:
                sec = sections_by_key.get((bcode, yname, sec_name))
                if not sec:
                    continue
                sef = _folder(f"Section {sec_name}", sf,
                              course_id=btech_id, branch_id=b.id, year_id=y.id,
                              semester_id=sems[sem_name].id, section_id=sec.id)
                for bt in BATCHES:
                    bt_obj = batches_by_key.get((bcode, yname, sec_name, bt))
                    if bt_obj:
                        _folder(bt, sef, batch_id=bt_obj.id)

    for bcode in ("CSE", "CS", "IT", "ECE", "EEE", "ME", "CE", "AIML", "DS"):
        _branch_tree(bcode, bcode)

    # ---------------- Demo notices ----------------
    if not Notice.query.first():
        db.session.add(Notice(
            title="College Closed — Founder's Day",
            description="The campus will remain closed on Friday for Founder's Day celebrations.",
            priority="important", created_by=admin_u.id, course_id=btech_id))

        db.session.add(Notice(
            title="Programming Assignment 03",
            description="Implement a singly linked list with insert/delete/traverse. "
                        "Submit before the deadline. This notice is ONLY for CSE 1st Year A2.",
            priority="urgent", created_by=t1.id,
            course_id=btech_id, branch_id=branches["CSE"].id,
            year_id=years["1st Year"].id, semester_id=sems["Sem 1"].id,
            section_id=sections_by_key[("CSE", "1st Year", "A")].id,
            batch_id=batches_by_key[("CSE", "1st Year", "A", "A2")].id,
            subject_id=prog.id))

        db.session.add(Notice(
            title="CSE 1st Year — Orientation Session",
            description="All CSE 1st year students must attend the orientation.",
            priority="normal", created_by=t1.id,
            course_id=btech_id, branch_id=branches["CSE"].id,
            year_id=years["1st Year"].id))

        db.session.add(Notice(
            title="Mid-Semester Exam Schedule Released",
            description="The mid-semester examination timetable is now available.",
            priority="important", created_by=admin_u.id, course_id=btech_id))

    # ---------------- Demo assignments ----------------
    if not Assignment.query.first():
        db.session.add(Assignment(
            title="Programming Assignment 03",
            description="Build the linked list implementation discussed in class.",
            due_date=datetime.utcnow() + timedelta(days=7),
            created_by=t1.id,
            course_id=btech_id, branch_id=branches["CSE"].id,
            year_id=years["1st Year"].id, semester_id=sems["Sem 1"].id,
            section_id=sections_by_key[("CSE", "1st Year", "A")].id,
            batch_id=batches_by_key[("CSE", "1st Year", "A", "A2")].id,
            subject_id=prog.id))

        db.session.add(Assignment(
            title="Math Assignment 01",
            description="Solve problems 1–15 from the textbook.",
            due_date=datetime.utcnow() + timedelta(days=10),
            created_by=t2.id,
            course_id=btech_id, branch_id=branches["CSE"].id,
            year_id=years["1st Year"].id, semester_id=sems["Sem 1"].id,
            section_id=sections_by_key[("CSE", "1st Year", "A")].id,
            batch_id=batches_by_key[("CSE", "1st Year", "A", "A1")].id,
            subject_id=math.id))

        db.session.add(Assignment(
            title="Data Structures Lab Record",
            description="Complete all 10 programs in the lab record.",
            due_date=datetime.utcnow() + timedelta(days=14),
            created_by=t1.id,
            course_id=btech_id, branch_id=branches["CSE"].id,
            year_id=years["2nd Year"].id, semester_id=sems["Sem 3"].id,
            subject_id=dsa.id))

    # ---------------- Timetable — NOTE teacher1.id is an int ----------------
    if not TimetableEntry.query.first():
        cse_a = sections_by_key[("CSE", "1st Year", "A")]
        entries = [
            ("Mon", "09:00", "10:00", "Room 201", prog.id, teacher1.id),
            ("Mon", "10:15", "11:15", "Room 201", math.id, teacher2.id),
            ("Mon", "11:30", "12:30", "Room 201", phy.id,  teacher1.id),
            ("Tue", "09:00", "10:00", "Lab 3",    prog.id, teacher1.id),
            ("Tue", "10:15", "11:15", "Room 201", math.id, teacher2.id),
            ("Wed", "09:00", "10:00", "Room 201", phy.id,  teacher1.id),
            ("Wed", "11:30", "12:30", "Room 202", math.id, teacher2.id),
            ("Thu", "09:00", "10:00", "Lab 3",    prog.id, teacher1.id),
            ("Fri", "10:15", "11:15", "Room 201", phy.id,  teacher1.id),
        ]
        for day, st, en, room, subj_id, tch_id in entries:
            db.session.add(TimetableEntry(
                day=day, start_time=st, end_time=en, room=room,
                subject_id=subj_id, teacher_id=tch_id,
                course_id=btech_id, branch_id=branches["CSE"].id,
                year_id=years["1st Year"].id, semester_id=sems["Sem 1"].id,
                section_id=cse_a.id))

    # ---------------- Sample student request ----------------
    if vishal and not StudentRequest.query.first():
        db.session.add(StudentRequest(
            student_id=vishal.id, category="Academic",
            subject="Need extra lab hours",
            description="Requesting additional lab access for programming practice."))

    # ---------------- Pre-configured Academic Folders ----------------
    if not Folder.query.first():
        f_timetable = Folder(name="Official College Timetables", created_by=admin_u.id)
        f_shared = Folder(name="General & Shared Resources", created_by=admin_u.id)
        f_common = Folder(
            name="Common First Year Resources",
            course_id=btech_id,
            year_id=years["1st Year"].id,
            created_by=admin_u.id
        )
        db.session.add_all([f_timetable, f_shared, f_common])
        db.session.flush()

        academic_branch_defs = [
            ("CSE", "Computer Science & Engineering (CSE)"),
            ("CS", "Computer Science (CS)"),
            ("IT", "Information Technology (IT)"),
            ("ECE", "Electronics & Communication (ECE)"),
            ("EEE", "Electrical & Electronics (EEE)"),
            ("ME", "Mechanical Engineering (ME)"),
            ("CE", "Civil Engineering (CE)"),
            ("AIML", "Artificial Intelligence & ML (AIML)"),
            ("DS", "Data Science (DS)"),
        ]

        for code, display_name in academic_branch_defs:
            b = branches.get(code)
            if not b:
                continue
            bf = Folder(name=display_name, course_id=btech_id, branch_id=b.id, created_by=admin_u.id)
            db.session.add(bf)
            db.session.flush()

            y1 = Folder(
                name="1st Year", parent_id=bf.id, course_id=btech_id,
                branch_id=b.id, year_id=years["1st Year"].id, created_by=admin_u.id
            )
            db.session.add(y1)
            db.session.flush()

            s1 = Folder(
                name="Sem 1 - Notes & Material", parent_id=y1.id, course_id=btech_id,
                branch_id=b.id, year_id=years["1st Year"].id, semester_id=sems["Sem 1"].id,
                created_by=admin_u.id
            )
            db.session.add(s1)
            db.session.flush()

            if code == "CSE":
                syl = Folder(
                    name="Syllabus & Complete Course Outline", parent_id=s1.id,
                    course_id=btech_id, branch_id=b.id, year_id=years["1st Year"].id,
                    semester_id=sems["Sem 1"].id, created_by=admin_u.id
                )
                db.session.add(syl)
                db.session.flush()

                y2 = Folder(
                    name="2nd Year", parent_id=bf.id, course_id=btech_id,
                    branch_id=b.id, year_id=years["2nd Year"].id, created_by=admin_u.id
                )
                db.session.add(y2)
                db.session.flush()

                s3 = Folder(
                    name="Sem 3 - Notes & Material", parent_id=y2.id, course_id=btech_id,
                    branch_id=b.id, year_id=years["2nd Year"].id, semester_id=sems["Sem 3"].id,
                    created_by=admin_u.id
                )
                db.session.add(s3)
                db.session.flush()

                dsa_folder = Folder(
                    name="Data Structures & Algorithms", parent_id=s3.id,
                    course_id=btech_id, branch_id=b.id, year_id=years["2nd Year"].id,
                    semester_id=sems["Sem 3"].id, created_by=admin_u.id
                )
                db.session.add(dsa_folder)
                db.session.flush()

    db.session.commit()

    print("")
    print("=" * 68)
    print("  Seed complete. Demo logins (password: password123)")
    print("=" * 68)
    print("  ADMIN     -> admin")
    print("  TEACHER   -> teacher1  (Dr. Anjali Verma, CSE)")
    print("  TEACHER   -> teacher2  (Prof. Rajesh Kumar, CSE)")
    print("")
    print("  STUDENTS (identity = enrollment number, NOT name):")
    print("    CSE2024001  Vishal Kumar   CSE  1st Yr  Sec A  Batch A2  (Student Admin)")
    print("    CSE2024002  Saksham Singh  CSE  1st Yr  Sec A  Batch A2")
    print("    CSE2024003  Rahul Sharma   CSE  1st Yr  Sec A  Batch A1")
    print("    CS2024001   Rahul Sharma   CS   1st Yr  Sec A  Batch A2  (different person!)")
    print("    IT2024001   Vikram Joshi   IT   1st Yr  Sec A  Batch A1")
    print("    ECE2024001  Pooja Reddy    ECE  1st Yr  Sec A  Batch A1")
    print("=" * 68)
    print("")
