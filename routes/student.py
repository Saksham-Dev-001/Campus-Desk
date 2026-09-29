from datetime import datetime
from services.time_utils import now_ist
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from sqlalchemy import or_
from models import (db, Student, Notice, Assignment, FileRecord, TimetableEntry,
                    Notification, StudentRequest, AssignmentSubmission, AuditLog,
                    Subject, Teacher)
from services.targeting import apply_target_filter
from services.storage import get_storage_provider
from extensions import cache

student_bp = Blueprint("student", __name__, url_prefix="/student")

DAY_NAMES = {
    0: ("Monday", "Mon"), 1: ("Tuesday", "Tue"), 2: ("Wednesday", "Wed"),
    3: ("Thursday", "Thu"), 4: ("Friday", "Fri"), 5: ("Saturday", "Sat"),
    6: ("Sunday", "Sun"),
}

def _me():
    s = Student.query.filter_by(user_id=current_user.id).first()
    if not s:
        abort(403)
    return s

def _allowed(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

def _time_key(e):
    return e.start_time or ""

@student_bp.route("/dashboard")
@login_required
def dashboard():
    s = _me()
    notices = apply_target_filter(Notice.query.filter(Notice.active == True), Notice, s) \
        .order_by(Notice.publish_date.desc()).limit(5).all()
    assignments = apply_target_filter(Assignment.query.filter(Assignment.status == "open"),
                                      Assignment, s) \
        .order_by(Assignment.due_date.asc().nullslast()).limit(5).all()
    materials = apply_target_filter(FileRecord.query, FileRecord, s) \
        .order_by(FileRecord.updated_at.desc()).limit(6).all()

    now = now_ist()
    today_short = DAY_NAMES[now.weekday()][1]
    timetable = apply_target_filter(
        TimetableEntry.query.filter(TimetableEntry.day == today_short),
        TimetableEntry, s).order_by(TimetableEntry.start_time).all()

    notifications = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).limit(6).all()

    hour = now.hour
    greeting = "Good Morning" if hour < 12 else ("Good Afternoon" if hour < 17 else "Good Evening")

    return render_template("dashboard_student.html", student=s,
                           notices=notices, assignments=assignments,
                           materials=materials, timetable=timetable,
                           notifications=notifications, greeting=greeting,
                           open_assignments=apply_target_filter(
                               Assignment.query.filter(Assignment.status == "open"),
                               Assignment, s).count(),
                           unread_notifs=Notification.query
                               .filter_by(user_id=current_user.id, read=False).count())

@student_bp.route("/notices")
@login_required
def notices():
    if current_user.role in ("teacher", "admin"):
        return redirect(url_for("teacher.notices"))
    s = _me()
    items = apply_target_filter(Notice.query.filter(Notice.active == True), Notice, s) \
        .order_by(Notice.publish_date.desc()).all()
    return render_template("notices.html", notices=items, mode="student")

def _subject_icon(name):
    n = (name or "").lower()
    if "chem" in n: return "🧪"
    if "math" in n: return "📐"
    if "comm" in n or "eng" in n: return "🗣️"
    if "program" in n or "python" in n or "c++" in n or "code" in n or "java" in n or "problem" in n: return "💻"
    if "electr" in n or "circuit" in n or "digital" in n: return "⚡"
    if "cyber" in n or "hack" in n or "secur" in n: return "🛡️"
    if "phys" in n: return "⚛️"
    if "mechan" in n or "civil" in n: return "⚙️"
    if "ai" in n or "data" in n or "ml" in n: return "🤖"
    if "lab" in n: return "🔬"
    return "📘"

@student_bp.route("/assignments")
@login_required
def assignments():
    if current_user.role in ("teacher", "admin"):
        return redirect(url_for("teacher.assignments"))
    s = _me()
    items = apply_target_filter(Assignment.query, Assignment, s) \
        .order_by(Assignment.due_date.asc().nullslast()).all()
    
    subs = {a.id: a.submission_for(s) for a in items}

    # Fetch all academic subjects for student's branch & semester
    sub_q = Subject.query.filter(
        or_(Subject.branch_id.is_(None), Subject.branch_id == s.branch_id),
        or_(Subject.semester_id.is_(None), Subject.semester_id == s.semester_id)
    )
    # Exclude non-academic periods like Library and ECA
    academic_subjects = [
        sub for sub in sub_q.order_by(Subject.name).all()
        if not (sub.code and (sub.code.startswith("LIB") or sub.code.startswith("ECA")))
    ]

    # Map each subject to its faculty from TimetableEntry
    subject_teacher_map = {}
    for sub in academic_subjects:
        tt = TimetableEntry.query.filter_by(
            branch_id=s.branch_id, 
            section_id=s.section_id, 
            subject_id=sub.id
        ).first()
        if tt and tt.teacher and tt.teacher.user:
            subject_teacher_map[sub.id] = tt.teacher.user.name
        else:
            subject_teacher_map[sub.id] = "Faculty"

    # Organize assignments by subject
    subject_map = {sub.id: sub for sub in academic_subjects}
    by_subject = {sub.id: [] for sub in academic_subjects}
    general_assignments = []

    for a in items:
        if a.subject_id and a.subject_id in by_subject:
            by_subject[a.subject_id].append(a)
        elif a.subject_id and a.subject_id in subject_map:
            by_subject[a.subject_id].append(a)
        elif a.subject_id:
            sub_obj = db.session.get(Subject, a.subject_id)
            if sub_obj:
                subject_map[sub_obj.id] = sub_obj
                by_subject[sub_obj.id] = [a]
                subject_teacher_map[sub_obj.id] = a.author.name if a.author else "Faculty"
            else:
                general_assignments.append(a)
        else:
            general_assignments.append(a)

    subject_wise_list = []
    for sub_id, sub in subject_map.items():
        asgs = by_subject.get(sub_id, [])
        sub_count = sum(1 for a in asgs if subs.get(a.id) is not None)
        pend_count = sum(1 for a in asgs if subs.get(a.id) is None and a.status == "open")
        subject_wise_list.append({
            "id": sub.id,
            "name": sub.name,
            "code": sub.code or "",
            "icon": _subject_icon(sub.name),
            "teacher": subject_teacher_map.get(sub_id, "Faculty"),
            "assignments": asgs,
            "total_count": len(asgs),
            "submitted_count": sub_count,
            "pending_count": pend_count,
        })

    # Sort: subjects with assignments first, then alphabetically
    subject_wise_list.sort(key=lambda x: (-x["total_count"], x["name"]))

    # Overall stats for student
    total_asgs = len(items)
    total_submitted = sum(1 for a in items if subs.get(a.id) is not None)
    total_pending = sum(1 for a in items if subs.get(a.id) is None and a.status == "open")

    return render_template(
        "assignments.html",
        assignments=items,
        submissions=subs,
        subject_wise=subject_wise_list,
        general_assignments=general_assignments,
        total_asgs=total_asgs,
        total_submitted=total_submitted,
        total_pending=total_pending,
        student=s,
        mode="student"
    )

@student_bp.route("/assignments/<int:aid>/submit", methods=["POST"])
@login_required
def submit_assignment(aid):
    flash("Assignments are submitted offline directly to your teacher in class. Your teacher will verify and grade your submission here.", "info")
    return redirect(url_for("student.assignments"))

@student_bp.route("/timetable")
@login_required
def timetable():
    if current_user.role in ("teacher", "admin"):
        return redirect(url_for("teacher.timetable"))
    s = _me()

    entries = apply_target_filter(TimetableEntry.query, TimetableEntry, s) \
        .order_by(TimetableEntry.start_time).all()
    entries.sort(key=_time_key)

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    grid = {d: sorted([e for e in entries if e.day == d], key=_time_key) for d in days}

    now = now_ist()
    today_long, today_short = DAY_NAMES[now.weekday()]
    today_entries = grid.get(today_short, [])
    now_str = now.strftime("%H:%M")

    official = apply_target_filter(
        FileRecord.query.filter(
            FileRecord.filename.like("Official Timetable%"),
            FileRecord.status == "active"
        ), FileRecord, s
    ).order_by(FileRecord.updated_at.desc()).all()

    return render_template(
        "timetable.html",
        grid=grid, days=days, mode="student",
        today_name=today_long, today_date=now.strftime("%d %B %Y"),
        today_short=today_short, today_entries=today_entries,
        now_str=now_str, official_files=official,
    )

@student_bp.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).all()
    unread = sum(1 for n in items if not n.read)
    return render_template("notifications.html", notifications=items, unread=unread)

@student_bp.route("/notifications/read/<int:nid>", methods=["POST"])
@login_required
def mark_read(nid):
    n = Notification.query.filter_by(id=nid, user_id=current_user.id).first_or_404()
    n.read = True
    db.session.commit()
    return redirect(n.link or url_for("student.notifications"))

@student_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, read=False).update({"read": True})
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("student.notifications"))

@student_bp.route("/requests", methods=["GET", "POST"])
@login_required
def requests_():
    if current_user.role in ("teacher", "admin"):
        return redirect(url_for("teacher.requests_"))
    s = _me()
    if request.method == "POST":
        subject = (request.form.get("subject") or "").strip()
        if not subject:
            flash("Subject is required.", "error")
        else:
            db.session.add(StudentRequest(
                student_id=s.id,
                category=(request.form.get("category") or "General").strip(),
                subject=subject[:160],
                description=(request.form.get("description") or "").strip()))
            db.session.commit()
            flash("Request submitted.", "success")
        return redirect(url_for("student.requests_"))
    return render_template("requests.html",
                           requests=StudentRequest.query.filter_by(student_id=s.id)
                               .order_by(StudentRequest.created_at.desc()).all(),
                           mode="student")

@student_bp.route("/profile")
@login_required
def profile():
    s = _me()
    return render_template("profile.html", student=s,
                           submitted_count=AssignmentSubmission.query.filter_by(student_id=s.id).count(),
                           requests_count=StudentRequest.query.filter_by(student_id=s.id).count())
