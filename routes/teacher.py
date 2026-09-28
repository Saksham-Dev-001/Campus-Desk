"""Teacher routes — dashboard, notices (now announcements), assignments, timetable."""
import csv
import io
import re
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, current_app, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from models import (db, Notice, Assignment, TimetableEntry, Student, Teacher,
                    FileRecord, StudentRequest, Notification, AuditLog,
                    AssignmentSubmission, Subject, Branch)
from services.targeting import parse_target_from_form, visible_students, enforce_teacher_scope
from services.storage import get_storage_provider
from extensions import cache

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")

DAY_NAMES = {
    0: ("Monday", "Mon"), 1: ("Tuesday", "Tue"), 2: ("Wednesday", "Wed"),
    3: ("Thursday", "Thu"), 4: ("Friday", "Fri"), 5: ("Saturday", "Sat"),
    6: ("Sunday", "Sun"),
}
DAY_ALIASES = {
    "monday": "Mon", "mon": "Mon",
    "tuesday": "Tue", "tue": "Tue", "tues": "Tue",
    "wednesday": "Wed", "wed": "Wed",
    "thursday": "Thu", "thu": "Thu", "thur": "Thu", "thurs": "Thu",
    "friday": "Fri", "fri": "Fri",
    "saturday": "Sat", "sat": "Sat",
    "sunday": "Sun", "sun": "Sun",
}
VALID_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

def _require_teacher():
    if current_user.role not in ("teacher", "admin"):
        abort(403)

def _audit(action, entity=None, eid=None, details=None):
    db.session.add(AuditLog(user_id=current_user.id, action=action,
                            entity=entity, entity_id=eid, details=details))

def _allowed_image(fn):
    if not fn or "." not in fn:
        return False
    return fn.rsplit(".", 1)[1].lower() in ("png", "jpg", "jpeg", "webp", "gif")

def _time_key(e):
    return e.start_time or ""

def _normalize_day(raw):
    if not raw:
        return None
    key = raw.strip().lower()
    return DAY_ALIASES.get(key) or DAY_ALIASES.get(key[:3])

def _normalize_time(raw):
    if not raw:
        return None
    s = str(raw).strip().lower().replace(".", ":")
    m = re.search(r"(\d{1,2})\s*:\s*(\d{2})\s*(am|pm)?", s)
    if not m:
        return None
    h = int(m.group(1)); mi = int(m.group(2)); ap = m.group(3)
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None
    return "{:02d}:{:02d}".format(h, mi)

def _match_subject(text, branch_id=None, semester_id=None):
    if not text:
        return None
    t = text.strip().lower()
    if not t:
        return None
    q = Subject.query
    if branch_id:
        q = q.filter((Subject.branch_id == branch_id) | (Subject.branch_id.is_(None)))
    if semester_id:
        q = q.filter((Subject.semester_id == semester_id) | (Subject.semester_id.is_(None)))
    candidates = q.all()
    for s in candidates:
        if s.name.lower() == t:
            return s
    for s in candidates:
        if s.name.lower() in t or t in s.name.lower():
            return s
    t_tokens = set(re.findall(r"[a-z]{3,}", t))
    best = None
    best_score = 0.0
    for s in candidates:
        s_tokens = set(re.findall(r"[a-z]{3,}", s.name.lower()))
        if not s_tokens:
            continue
        overlap = len(t_tokens & s_tokens) / float(len(s_tokens))
        if overlap > best_score:
            best_score = overlap
            best = s
    if best and best_score >= 0.6:
        return best
    return None

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@teacher_bp.route("/dashboard")
@login_required
def dashboard():
    _require_teacher()
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()

    rf_q = FileRecord.query.filter(FileRecord.status == "active")
    for x in ("Official Timetable", "Announcement", "[CampusDesk]"):
        rf_q = rf_q.filter(~FileRecord.filename.ilike(x + "%"))
    if teacher and teacher.branch_id:
        rf_q = rf_q.filter(or_(FileRecord.branch_id.is_(None), FileRecord.branch_id == teacher.branch_id))
    recent_files = rf_q.order_by(FileRecord.updated_at.desc()).limit(5).all()

    total_students = Student.query.filter_by(branch_id=teacher.branch_id).count() if (teacher and teacher.branch_id) else Student.query.count()

    nq = Notice.query.filter_by(active=True)
    if teacher and teacher.branch_id:
        nq = nq.filter(or_(Notice.branch_id.is_(None), Notice.branch_id == teacher.branch_id))
    notices = nq.order_by(Notice.publish_date.desc()).limit(5).all()

    aq = Assignment.query
    if teacher and teacher.branch_id:
        aq = aq.filter(or_(Assignment.branch_id.is_(None), Assignment.branch_id == teacher.branch_id))
    assignments = aq.order_by(Assignment.publish_date.desc()).limit(5).all()

    return render_template("dashboard_teacher.html", teacher=teacher,
                           total_students=total_students,
                           notices=notices,
                           assignments=assignments,
                           recent_files=recent_files,
                           pending_requests=StudentRequest.query.filter_by(status="pending").count(),
                           total_submissions=AssignmentSubmission.query.count())

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@teacher_bp.route("/profile")
@login_required
def profile():
    _require_teacher()
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    assigned_subjects = current_user.allowed_subjects()
    allowed_branches = current_user.allowed_branches()

    my_uploads_count = FileRecord.query.filter_by(uploaded_by=current_user.id, status="active").count()
    my_notices_count = Notice.query.filter_by(created_by=current_user.id).count()
    my_assignments_count = Assignment.query.filter_by(created_by=current_user.id).count()
    my_submissions_count = db.session.query(AssignmentSubmission).join(
        Assignment, AssignmentSubmission.assignment_id == Assignment.id
    ).filter(Assignment.created_by == current_user.id).count()

    total_lectures_count = TimetableEntry.query.filter_by(teacher_id=teacher.id).count() if teacher else 0

    return render_template("teacher_profile.html",
                           teacher=teacher,
                           assigned_subjects=assigned_subjects,
                           allowed_branches=allowed_branches,
                           my_uploads_count=my_uploads_count,
                           my_notices_count=my_notices_count,
                           my_assignments_count=my_assignments_count,
                           my_submissions_count=my_submissions_count,
                           total_lectures_count=total_lectures_count)

# ---------------------------------------------------------------------------
# ANNOUNCEMENTS (formerly Notices)
# ---------------------------------------------------------------------------
@teacher_bp.route("/notices", methods=["GET", "POST"])
@login_required
def notices():
    _require_teacher()
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()

        if not title and not description:
            flash("Add a title or caption for the announcement.", "error")
            return redirect(url_for("teacher.notices"))

        targets = parse_target_from_form(request.form)
        if not current_user.is_admin:
            enforce_teacher_scope(current_user, targets.get("branch_id"))
        pub = request.form.get("publish_date")

        # ---- Optional image upload ----
        attachment_id = None
        img = request.files.get("image")
        if img and img.filename:
            if not _allowed_image(img.filename):
                flash("Only PNG, JPG, JPEG, WEBP or GIF images are allowed.", "error")
                return redirect(url_for("teacher.notices"))

            data = img.read()
            original = secure_filename(img.filename) or "announcement.png"
            provider = get_storage_provider(current_app.config)
            branch_code = None
            if targets.get("branch_id"):
                b = Branch.query.get(targets["branch_id"])
                if b:
                    branch_code = b.code
            ref = provider.upload_file(data, original,
                                       branch_code=branch_code,
                                       folder_path="_announcements")

            fr = FileRecord(
                filename=original, original_filename=original,
                mime_type=img.mimetype, size_bytes=len(data),
                folder_id=None, storage_provider=provider.name, storage_ref=ref,
                uploaded_by=current_user.id, **targets,
            )
            db.session.add(fr)
            db.session.flush()
            attachment_id = fr.id

        # Fallback title from caption if empty
        if not title:
            title = (description[:77] + "…") if len(description) > 80 else description

        n = Notice(
            title=title[:200],
            description=description,
            priority=request.form.get("priority") or "normal",
            publish_date=datetime.fromisoformat(pub) if pub else datetime.utcnow(),
            attachment_file_id=attachment_id,
            created_by=current_user.id,
            **targets,
        )
        db.session.add(n)
        db.session.flush()
        _audit("notice.create", "Notice", n.id, title)
        _notify(n, "notice")
        db.session.commit()
        flash("Announcement published.", "success")
        return redirect(url_for("teacher.notices"))

    items = Notice.query.order_by(Notice.publish_date.desc()).all()
    return render_template("notices.html", notices=items, mode="teacher")

@teacher_bp.route("/notices/<int:nid>/delete", methods=["POST"])
@login_required
def delete_notice(nid):
    _require_teacher()
    n = Notice.query.get_or_404(nid)
    n.active = False
    _audit("notice.archive", "Notice", nid, n.title)
    db.session.commit()
    flash("Announcement archived.", "success")
    return redirect(url_for("teacher.notices"))


@teacher_bp.route("/notices/<int:nid>/edit", methods=["GET", "POST"])
@login_required
def edit_notice(nid):
    _require_teacher()
    n = Notice.query.get_or_404(nid)
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        if not title and not description:
            flash("Add a title or caption.", "error")
            return redirect(url_for("teacher.edit_notice", nid=nid))
        pub = request.form.get("publish_date")
        targets = parse_target_from_form(request.form)
        img = request.files.get("image")
        if img and img.filename:
            if not _allowed_image(img.filename):
                flash("Only PNG, JPG, JPEG, WEBP or GIF images are allowed.", "error")
                return redirect(url_for("teacher.edit_notice", nid=nid))
            data = img.read()
            original = secure_filename(img.filename) or "announcement.png"
            provider = get_storage_provider(current_app.config)
            branch_code = None
            if targets.get("branch_id"):
                b = Branch.query.get(targets["branch_id"])
                if b:
                    branch_code = b.code
            ref = provider.upload_file(data, original, branch_code=branch_code,
                                       folder_path="_announcements")
            fr = FileRecord(
                filename=original, original_filename=original,
                mime_type=img.mimetype, size_bytes=len(data),
                folder_id=None, storage_provider=provider.name, storage_ref=ref,
                uploaded_by=current_user.id, **targets,
            )
            db.session.add(fr)
            db.session.flush()
            n.attachment_file_id = fr.id
        n.title = (title or description[:77])[:200]
        n.description = description
        n.priority = request.form.get("priority") or n.priority
        if pub:
            n.publish_date = datetime.fromisoformat(pub)
        for k, v in targets.items():
            setattr(n, k, v)
        _audit("notice.edit", "Notice", n.id, n.title)
        db.session.commit()
        flash("Announcement updated.", "success")
        return redirect(url_for("teacher.notices"))
    return render_template("notice_edit.html", notice=n, mode="teacher")


@teacher_bp.route("/notices/<int:nid>/archive", methods=["POST"])
@login_required
def archive_notice(nid):
    """Hide from students (soft delete). Still visible in admin/audit."""
    _require_teacher()
    n = Notice.query.get_or_404(nid)
    n.active = False
    _audit("notice.archive", "Notice", nid, n.title)
    db.session.commit()
    flash("Announcement archived.", "success")
    return redirect(url_for("teacher.notices"))


@teacher_bp.route("/notices/<int:nid>/permanent-delete", methods=["POST"])
@login_required
def permanent_delete_notice(nid):
    """Permanent delete. Also removes attached image file."""
    _require_teacher()
    n = Notice.query.get_or_404(nid)
    if n.attachment:
        fr = n.attachment
        try:
            get_storage_provider(current_app.config).delete_file(fr.storage_ref)
        except Exception:
            pass
        n.attachment_file_id = None
        db.session.flush()
        db.session.delete(fr)
    _audit("notice.delete", "Notice", nid, n.title)
    db.session.delete(n)
    db.session.commit()
    flash("Announcement deleted permanently.", "success")
    return redirect(url_for("teacher.notices"))

# ---------------------------------------------------------------------------
# Assignments (Offline Submissions & Teacher Marking Workflow)
# ---------------------------------------------------------------------------
def _allowed_assignment_file(filename):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", set())

@teacher_bp.route("/assignments", methods=["GET", "POST"])
@login_required
def assignments():
    _require_teacher()
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        if not title:
            flash("Assignment title is required.", "error")
            return redirect(url_for("teacher.assignments"))

        targets = parse_target_from_form(request.form)
        if not current_user.is_admin:
            enforce_teacher_scope(current_user, targets.get("branch_id"))

        due = request.form.get("due_date")

        # Optional attachment file (PDF, Doc, Image, etc.)
        attachment_id = None
        att = request.files.get("attachment")
        if att and att.filename:
            if not _allowed_assignment_file(att.filename):
                flash("File format not supported. Allowed: PDF, Word (DOC/DOCX), Images, Excel, PPT, TXT, ZIP.", "error")
                return redirect(url_for("teacher.assignments"))
            data = att.read()
            original = secure_filename(att.filename) or "assignment_attachment"
            provider = get_storage_provider(current_app.config)
            branch_code = None
            if targets.get("branch_id"):
                b = Branch.query.get(targets["branch_id"])
                if b:
                    branch_code = b.code
            ref = provider.upload_file(data, original, branch_code=branch_code, folder_path="_assignments")
            fr = FileRecord(
                filename=original, original_filename=original,
                mime_type=att.mimetype, size_bytes=len(data),
                folder_id=None, storage_provider=provider.name, storage_ref=ref,
                uploaded_by=current_user.id, **targets,
            )
            db.session.add(fr)
            db.session.flush()
            attachment_id = fr.id

        a = Assignment(
            title=title[:200],
            description=(request.form.get("description") or "").strip(),
            due_date=datetime.fromisoformat(due) if due else None,
            attachment_file_id=attachment_id,
            status="open",
            created_by=current_user.id,
            **targets
        )
        db.session.add(a)
        db.session.flush()
        _audit("assignment.create", "Assignment", a.id, title)
        _notify(a, "assignment")
        db.session.commit()
        flash("Assignment published successfully.", "success")
        return redirect(url_for("teacher.assignments"))

    q = Assignment.query
    if not current_user.is_admin and current_user.role == "teacher":
        allowed = current_user.allowed_branch_ids()
        if allowed:
            q = q.filter(or_(Assignment.branch_id.is_(None), Assignment.branch_id.in_(allowed)))
    items = q.order_by(Assignment.publish_date.desc()).all()

    # Build rich offline roster & statistics for each assignment
    assignment_data = {}
    for a in items:
        targeted = visible_students(a)
        def _s_key(st):
            r = st.enrollment_number or ""
            d = "".join(filter(str.isdigit, r))
            return (int(d) if d else 999999, (st.user.name if st.user else "").lower())
        targeted.sort(key=_s_key)

        subs_map = {sub.student_id: sub for sub in a.submissions}
        roster = []
        submitted_count = 0
        for st in targeted:
            sub = subs_map.get(st.id)
            if sub:
                submitted_count += 1
            roster.append({
                "student": st,
                "submission": sub,
                "is_submitted": sub is not None,
            })

        total_targeted = len(targeted)
        pct = int((submitted_count / total_targeted * 100)) if total_targeted > 0 else 0
        assignment_data[a.id] = {
            "roster": roster,
            "total_targeted": total_targeted,
            "total_submitted": submitted_count,
            "total_pending": max(0, total_targeted - submitted_count),
            "percent": pct,
        }

    return render_template(
        "assignments.html",
        assignments=items,
        assignment_data=assignment_data,
        submissions_by_assignment={a.id: a.submissions for a in items},
        mode="teacher"
    )

@teacher_bp.route("/assignments/<int:aid>/mark-student", methods=["POST"])
@login_required
def mark_student_submission(aid):
    _require_teacher()
    a = Assignment.query.get_or_404(aid)
    if not current_user.is_admin and current_user.role == "teacher":
        if a.branch_id and not current_user.can_write_branch(a.branch_id):
            abort(403)

    is_ajax = (request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json)
    json_data = request.get_json(silent=True) or {}

    student_id = request.form.get("student_id", type=int) or json_data.get("student_id")
    if not student_id:
        if is_ajax:
            return jsonify({"ok": False, "error": "Student ID required"}), 400
        flash("Student not specified.", "error")
        return redirect(url_for("teacher.assignments"))

    st = Student.query.get_or_404(student_id)
    action = request.form.get("action") or json_data.get("action") or "mark"
    grade = (request.form.get("grade") or json_data.get("grade") or "").strip()[:10]
    feedback = (request.form.get("feedback") or json_data.get("feedback") or "").strip()[:1000]

    existing = AssignmentSubmission.query.filter_by(assignment_id=a.id, student_id=st.id).first()

    if action == "unmark":
        if existing:
            db.session.delete(existing)
            _audit("assignment.unmark_student", "AssignmentSubmission", existing.id, f"{st.enrollment_number} for {a.title}")
            db.session.commit()
            if is_ajax:
                return jsonify({"ok": True, "action": "unmarked", "student_id": st.id})
            flash(f"Submission unmarked for {st.user.name}.", "info")
            return redirect(url_for("teacher.assignments"))
        if is_ajax:
            return jsonify({"ok": True, "action": "unmarked", "student_id": st.id})
        return redirect(url_for("teacher.assignments"))

    # action is "mark" or "grade"
    if existing:
        if grade or feedback:
            existing.grade = grade
            existing.feedback = feedback
            existing.status = "graded" if grade else "submitted"
        else:
            existing.status = "submitted"
        sub = existing
    else:
        sub = AssignmentSubmission(
            assignment_id=a.id,
            student_id=st.id,
            status="graded" if grade else "submitted",
            grade=grade or None,
            feedback=feedback or None,
            note="Offline submission verified by teacher",
            submitted_at=datetime.utcnow()
        )
        db.session.add(sub)

    _audit("assignment.mark_offline", "AssignmentSubmission", a.id, f"{st.enrollment_number} by {current_user.username}")

    if st.user_id:
        msg = f"Your offline submission was verified by {current_user.name}."
        if grade:
            msg += f" Grade: {grade}"
        db.session.add(Notification(
            user_id=st.user_id,
            kind="grade" if grade else "submission",
            title=f"Assignment Verified: {a.title}",
            message=msg,
            link=url_for("student.assignments")
        ))
    db.session.commit()

    if is_ajax:
        return jsonify({
            "ok": True,
            "action": "marked",
            "student_id": st.id,
            "grade": sub.grade or "",
            "feedback": sub.feedback or "",
            "status": sub.status,
            "submitted_at": sub.submitted_at.strftime("%d %b %Y, %H:%M")
        })

    flash(f"Submission verified for {st.user.name}.", "success")
    return redirect(url_for("teacher.assignments"))

@teacher_bp.route("/assignments/<int:aid>/mark-all", methods=["POST"])
@login_required
def mark_all_students(aid):
    _require_teacher()
    a = Assignment.query.get_or_404(aid)
    if not current_user.is_admin and current_user.role == "teacher":
        if a.branch_id and not current_user.can_write_branch(a.branch_id):
            abort(403)

    targeted = visible_students(a)
    subs_map = {s.student_id: s for s in a.submissions}
    new_count = 0
    now = datetime.utcnow()

    for st in targeted:
        if st.id not in subs_map:
            sub = AssignmentSubmission(
                assignment_id=a.id,
                student_id=st.id,
                status="submitted",
                note="Offline submission verified by teacher (Bulk)",
                submitted_at=now
            )
            db.session.add(sub)
            new_count += 1
            if st.user_id:
                db.session.add(Notification(
                    user_id=st.user_id,
                    kind="submission",
                    title=f"Assignment Verified: {a.title}",
                    message=f"Your offline submission was verified by {current_user.name}.",
                    link=url_for("student.assignments")
                ))

    _audit("assignment.mark_all", "Assignment", a.id, f"Marked {new_count} students")
    db.session.commit()
    flash(f"Marked {new_count} pending student(s) as submitted.", "success")
    return redirect(url_for("teacher.assignments"))

@teacher_bp.route("/assignments/<int:aid>/close", methods=["POST"])
@login_required
def close_assignment(aid):
    _require_teacher()
    a = Assignment.query.get_or_404(aid)
    if not current_user.is_admin and current_user.role == "teacher":
        if a.branch_id and not current_user.can_write_branch(a.branch_id):
            abort(403)
    a.status = "closed"
    _audit("assignment.close", "Assignment", aid, a.title)
    db.session.commit()
    flash("Assignment closed.", "success")
    return redirect(url_for("teacher.assignments"))

@teacher_bp.route("/assignments/<int:aid>/reopen", methods=["POST"])
@login_required
def reopen_assignment(aid):
    _require_teacher()
    a = Assignment.query.get_or_404(aid)
    if not current_user.is_admin and current_user.role == "teacher":
        if a.branch_id and not current_user.can_write_branch(a.branch_id):
            abort(403)
    a.status = "open"
    _audit("assignment.reopen", "Assignment", aid, a.title)
    db.session.commit()
    flash("Assignment reopened.", "success")
    return redirect(url_for("teacher.assignments"))

@teacher_bp.route("/assignments/<int:aid>/delete", methods=["POST"])
@login_required
def delete_assignment(aid):
    _require_teacher()
    a = Assignment.query.get_or_404(aid)
    if not current_user.is_admin and current_user.role == "teacher":
        if a.branch_id and not current_user.can_write_branch(a.branch_id):
            abort(403)
    title = a.title
    if a.attachment:
        fr = a.attachment
        try:
            get_storage_provider(current_app.config).delete_file(fr.storage_ref)
        except Exception:
            pass
        a.attachment_file_id = None
        db.session.flush()
        db.session.delete(fr)

    _audit("assignment.delete", "Assignment", aid, title)
    db.session.delete(a)
    db.session.commit()
    flash(f"Assignment '{title}' deleted.", "success")
    return redirect(url_for("teacher.assignments"))

@teacher_bp.route("/submissions/<int:sid>/grade", methods=["POST"])
@login_required
def grade_submission(sid):
    _require_teacher()
    sub = AssignmentSubmission.query.get_or_404(sid)
    sub.grade = (request.form.get("grade") or "").strip()[:10]
    sub.feedback = (request.form.get("feedback") or "").strip()[:1000]
    sub.status = "graded" if sub.grade else "submitted"
    _audit("submission.grade", "AssignmentSubmission", sid, sub.grade)
    db.session.commit()
    if sub.student and sub.student.user_id:
        db.session.add(Notification(
            user_id=sub.student.user_id, kind="grade",
            title="Graded: " + sub.assignment.title,
            message=("Grade: " + sub.grade) if sub.grade else "Feedback added",
            link=url_for("student.assignments"),
        ))
        db.session.commit()
    flash("Submission updated.", "success")
    return redirect(url_for("teacher.assignments"))

# ---------------------------------------------------------------------------
# TIMETABLE
# ---------------------------------------------------------------------------
def _render_timetable(mode, **extra):
    t_teacher = Teacher.query.filter_by(user_id=current_user.id).first() if (current_user.is_authenticated and current_user.role == "teacher") else None

    scope = request.args.get("scope", "my" if t_teacher else "all")
    branch_id = request.args.get("branch_id", type=int)

    q = TimetableEntry.query
    if mode == "teacher" and t_teacher and scope == "my":
        q = q.filter_by(teacher_id=t_teacher.id)
    elif branch_id:
        q = q.filter_by(branch_id=branch_id)
    elif mode == "teacher" and t_teacher and not t_teacher.is_global and t_teacher.branch_id:
        allowed = current_user.allowed_branch_ids()
        if allowed:
            q = q.filter(or_(TimetableEntry.branch_id.is_(None), TimetableEntry.branch_id.in_(allowed)))

    entries = q.options(
        joinedload(TimetableEntry.teacher).joinedload(Teacher.user),
        joinedload(TimetableEntry.subject),
        joinedload(TimetableEntry.branch),
        joinedload(TimetableEntry.section),
        joinedload(TimetableEntry.batch)
    ).order_by(TimetableEntry.start_time).all()

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    def _group_entries(entries_list):
        grouped = []
        by_slot = {}
        for e in entries_list:
            sec_name = e.section.name if e.section else None
            key = (e.day, e.start_time, e.end_time, e.room, e.subject_id, e.teacher_id, sec_name)
            if key not in by_slot:
                item = {
                    "id": e.id,
                    "day": e.day,
                    "start_time": e.start_time,
                    "end_time": e.end_time,
                    "room": e.room,
                    "subject": e.subject,
                    "teacher": e.teacher,
                    "branches": [e.branch.code] if e.branch else [],
                    "section": e.section.name if e.section else None,
                    "batch": e.batch.name if e.batch else None,
                    "raw_entry": e,
                }
                by_slot[key] = item
                grouped.append(item)
            else:
                if e.branch and e.branch.code not in by_slot[key]["branches"]:
                    by_slot[key]["branches"].append(e.branch.code)
        return sorted(grouped, key=lambda x: x["start_time"])

    grid = {d: _group_entries([e for e in entries if e.day == d]) for d in days}

    now = datetime.now()
    today_long, today_short = DAY_NAMES[now.weekday()]
    selected_day = request.args.get("day") or (today_short if today_short in VALID_DAYS else "Mon")
    today_entries = grid.get(selected_day, [])

    my_lectures_count = TimetableEntry.query.filter_by(teacher_id=t_teacher.id).count() if t_teacher else 0

    off_q = FileRecord.query.filter(
        FileRecord.filename.like("Official Timetable%"),
        FileRecord.status == "active"
    )
    if t_teacher and t_teacher.branch_id:
        off_q = off_q.filter(or_(FileRecord.branch_id.is_(None), FileRecord.branch_id == t_teacher.branch_id))
    official = off_q.order_by(FileRecord.updated_at.desc()).all()

    return render_template(
        "timetable.html",
        grid=grid, days=days, mode=mode,
        today_name=today_long,
        today_date=now.strftime("%d %B %Y"),
        today_short=today_short,
        selected_day=selected_day,
        today_entries=today_entries,
        official_files=official,
        scope=scope,
        my_lectures_count=my_lectures_count,
        branches=Branch.query.order_by(Branch.code).all(),
        selected_branch=branch_id,
        DAY_NAMES=DAY_NAMES,
        **extra
    )

@teacher_bp.route("/timetable")
@login_required
def timetable():
    _require_teacher()
    return _render_timetable("teacher")

@teacher_bp.route("/timetable/add", methods=["POST"])
@login_required
def timetable_add():
    _require_teacher()
    targets = parse_target_from_form(request.form)
    if not current_user.is_admin:
        enforce_teacher_scope(current_user, targets.get("branch_id"))
    day = request.form.get("day")
    start = _normalize_time(request.form.get("start_time"))
    end = _normalize_time(request.form.get("end_time"))
    if not (day in VALID_DAYS and start and end):
        flash("Day, start and end time are required.", "error")
        return redirect(url_for("teacher.timetable"))
    e = TimetableEntry(day=day, start_time=start, end_time=end,
                       room=request.form.get("room"), **targets)
    db.session.add(e); db.session.flush()
    _audit("timetable.create", "TimetableEntry", e.id)
    _notify(e, "timetable")
    db.session.commit()
    cache.delete('timetable_grid')
    flash("Timetable entry added.", "success")
    return redirect(url_for("teacher.timetable"))

@teacher_bp.route("/timetable/<int:eid>/delete", methods=["POST"])
@login_required
def delete_timetable(eid):
    _require_teacher()
    e = TimetableEntry.query.get_or_404(eid)
    db.session.delete(e)
    _audit("timetable.delete", "TimetableEntry", eid)
    db.session.commit()
    cache.delete('timetable_grid')
    flash("Entry deleted.", "success")
    return redirect(url_for("teacher.timetable"))

def _parse_bulk(text, default_day, branch_id, semester_id):
    LINE_RE_DAY_TIME = re.compile(
        r"^\s*(?P<day>[A-Za-z]+)\s*[|,\t]?\s*"
        r"(?P<start>\d{1,2}[:.]\d{2})\s*(?:am|pm)?\s*[-–to]+\s*"
        r"(?P<end>\d{1,2}[:.]\d{2})\s*(?:am|pm)?\s*[|,\t]?\s*"
        r"(?P<rest>.*)$",
        re.IGNORECASE,
    )
    LINE_RE_TIME_ONLY = re.compile(
        r"^\s*(?P<start>\d{1,2}[:.]\d{2})\s*(?:am|pm)?\s*[-–to]+\s*"
        r"(?P<end>\d{1,2}[:.]\d{2})\s*(?:am|pm)?\s*[|,\t]?\s*"
        r"(?P<rest>.*)$",
        re.IGNORECASE,
    )
    ROOM_RE = re.compile(r"\b(room|lab|hall|lt|sl|cr)[\s\-]*([A-Za-z0-9\-]+)\b", re.IGNORECASE)

    entries = []
    errors = []
    current_day = default_day if default_day in VALID_DAYS else "Mon"

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower() in ("day", "time", "subject", "room", "teacher"):
            continue
        m = LINE_RE_DAY_TIME.match(line)
        day = None; start = end = None; rest = ""
        if m:
            day = _normalize_day(m.group("day"))
            start = _normalize_time(m.group("start"))
            end = _normalize_time(m.group("end"))
            rest = m.group("rest") or ""
        else:
            m2 = LINE_RE_TIME_ONLY.match(line)
            if m2:
                day = current_day
                start = _normalize_time(m2.group("start"))
                end = _normalize_time(m2.group("end"))
                rest = m2.group("rest") or ""
            else:
                m3 = re.match(r"^\s*(?P<day>[A-Za-z]+)\s+(?P<rest>.*?)(?P<start>\d{1,2}[:.]\d{2})\s*[-–to]+\s*(?P<end>\d{1,2}[:.]\d{2})",
                              line, re.IGNORECASE)
                if m3:
                    day = _normalize_day(m3.group("day"))
                    start = _normalize_time(m3.group("start"))
                    end = _normalize_time(m3.group("end"))
                    rest = m3.group("rest") or ""

        if not day or not start or not end:
            errors.append("Could not parse: " + line[:80])
            continue
        current_day = day

        room = None
        rm = ROOM_RE.search(rest)
        if rm:
            room = (rm.group(1) + " " + rm.group(2)).strip()
            rest = (rest[:rm.start()] + " " + rest[rm.end():]).strip()

        rest = re.sub(r"[|,;\t]+", " ", rest).strip()
        rest = re.sub(r"\s{2,}", " ", rest)
        subject = _match_subject(rest, branch_id=branch_id, semester_id=semester_id)
        entries.append({
            "day": day, "start": start, "end": end, "room": room,
            "subject_id": subject.id if subject else None,
            "raw": rest, "matched": subject.name if subject else None,
        })
    return entries, errors

@teacher_bp.route("/timetable/bulk", methods=["POST"])
@login_required
def timetable_bulk():
    _require_teacher()
    text = request.form.get("bulk_text") or ""
    default_day = request.form.get("default_day") or "Mon"
    targets = parse_target_from_form(request.form)
    branch_id = targets.get("branch_id")
    semester_id = targets.get("semester_id")
    entries, errors = _parse_bulk(text, default_day, branch_id, semester_id)
    if not entries:
        flash("Nothing parsed. Check the format — one class per line.", "error")
        for e in errors[:5]:
            flash(e, "error")
        return redirect(url_for("teacher.timetable"))

    wipe_q = TimetableEntry.query
    for k, v in targets.items():
        if v is None:
            wipe_q = wipe_q.filter(getattr(TimetableEntry, k).is_(None))
        else:
            wipe_q = wipe_q.filter(getattr(TimetableEntry, k) == v)
    wiped = wipe_q.delete(synchronize_session=False)

    for e in entries:
        db.session.add(TimetableEntry(
            day=e["day"], start_time=e["start"], end_time=e["end"],
            room=e["room"], subject_id=e["subject_id"], **targets
        ))
    _audit("timetable.bulk", "TimetableEntry",
           details="wiped {} created {}".format(wiped, len(entries)))
    db.session.commit()
    cache.delete('timetable_grid')
    flash("Imported {} entries (replaced {}).".format(len(entries), wiped), "success")
    return redirect(url_for("teacher.timetable"))

@teacher_bp.route("/timetable/csv", methods=["POST"])
@login_required
def timetable_csv():
    _require_teacher()
    f = request.files.get("csv")
    if not f:
        flash("Choose a CSV file.", "error")
        return redirect(url_for("teacher.timetable"))
    targets = parse_target_from_form(request.form)
    try:
        raw = f.read().decode("utf-8-sig")
    except Exception as e:
        flash("Could not read CSV: " + str(e), "error")
        return redirect(url_for("teacher.timetable"))
    reader = csv.DictReader(io.StringIO(raw))
    entries = []
    for i, row in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        day = _normalize_day(row.get("day"))
        start = _normalize_time(row.get("start") or row.get("start_time"))
        end = _normalize_time(row.get("end") or row.get("end_time"))
        if not (day and start and end):
            continue
        subj_text = row.get("subject") or ""
        subject = _match_subject(subj_text, branch_id=targets.get("branch_id"),
                                 semester_id=targets.get("semester_id"))
        entries.append({
            "day": day, "start": start, "end": end,
            "room": row.get("room") or None,
            "subject_id": subject.id if subject else None,
        })
    if not entries:
        flash("No valid rows found in CSV.", "error")
        return redirect(url_for("teacher.timetable"))

    wipe_q = TimetableEntry.query
    for k, v in targets.items():
        if v is None:
            wipe_q = wipe_q.filter(getattr(TimetableEntry, k).is_(None))
        else:
            wipe_q = wipe_q.filter(getattr(TimetableEntry, k) == v)
    wiped = wipe_q.delete(synchronize_session=False)

    for e in entries:
        db.session.add(TimetableEntry(
            day=e["day"], start_time=e["start"], end_time=e["end"],
            room=e["room"], subject_id=e["subject_id"], **targets
        ))
    db.session.commit()
    cache.delete('timetable_grid')
    flash("Imported {} entries from CSV.".format(len(entries)), "success")
    return redirect(url_for("teacher.timetable"))

@teacher_bp.route("/timetable/official", methods=["POST"])
@login_required
def timetable_official():
    _require_teacher()
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Choose a PDF or image.", "error")
        return redirect(url_for("teacher.timetable"))
    if "." not in f.filename:
        flash("File must have an extension.", "error")
        return redirect(url_for("teacher.timetable"))
    ext = f.filename.rsplit(".", 1)[1].lower()
    if ext not in ("pdf", "png", "jpg", "jpeg", "webp"):
        flash("Only PDF or image allowed.", "error")
        return redirect(url_for("teacher.timetable"))

    targets = parse_target_from_form(request.form)
    if not current_user.is_admin:
        enforce_teacher_scope(current_user, targets.get("branch_id"))
    data = f.read()
    original = secure_filename(f.filename) or "timetable.pdf"
    display = "Official Timetable"
    branch_code = None
    if targets.get("branch_id"):
        b = Branch.query.get(targets["branch_id"])
        if b:
            display += " - " + b.code
            branch_code = b.code
    display += "." + ext

    provider = get_storage_provider(current_app.config)
    ref = provider.upload_file(data, original, branch_code=branch_code,
                               folder_path="_official")

    prev_q = FileRecord.query.filter(FileRecord.filename.like("Official Timetable%"))
    for k, v in targets.items():
        if v is None:
            prev_q = prev_q.filter(getattr(FileRecord, k).is_(None))
        else:
            prev_q = prev_q.filter(getattr(FileRecord, k) == v)
    for prev in prev_q.all():
        Notice.query.filter_by(attachment_file_id=prev.id).update({"attachment_file_id": None})
        Assignment.query.filter_by(attachment_file_id=prev.id).update({"attachment_file_id": None})
        StudentRequest.query.filter_by(attachment_file_id=prev.id).update({"attachment_file_id": None})
        AssignmentSubmission.query.filter_by(file_id=prev.id).update({"file_id": None})
        try:
            provider.delete_file(prev.storage_ref)
        except Exception:
            pass
        db.session.delete(prev)

    rec = FileRecord(
        filename=display, original_filename=original,
        mime_type=f.mimetype, size_bytes=len(data),
        folder_id=None, storage_provider=provider.name, storage_ref=ref,
        uploaded_by=current_user.id, **targets
    )
    db.session.add(rec)
    _audit("timetable.official", "FileRecord", details=display)
    db.session.commit()
    flash("Official timetable uploaded.", "success")
    return redirect(url_for("teacher.timetable"))

@teacher_bp.route("/timetable/official/<int:fid>/delete", methods=["POST"])
@login_required
def timetable_official_delete(fid):
    _require_teacher()
    rec = FileRecord.query.get_or_404(fid)
    if current_user.role in ("teacher", "student_admin") and not current_user.is_admin:
        if not current_user.can_write_branch(rec.branch_id):
            abort(403)
    Notice.query.filter_by(attachment_file_id=rec.id).update({"attachment_file_id": None})
    Assignment.query.filter_by(attachment_file_id=rec.id).update({"attachment_file_id": None})
    StudentRequest.query.filter_by(attachment_file_id=rec.id).update({"attachment_file_id": None})
    AssignmentSubmission.query.filter_by(file_id=rec.id).update({"file_id": None})
    try:
        get_storage_provider(current_app.config).delete_file(rec.storage_ref)
    except Exception:
        pass
    _audit("timetable.official.delete", "FileRecord", fid, rec.filename)
    db.session.delete(rec)
    db.session.commit()
    flash("Removed.", "success")
    return redirect(url_for("teacher.timetable"))

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------
@teacher_bp.route("/requests", methods=["GET", "POST"])
@login_required
def requests_():
    _require_teacher()
    if request.method == "POST":
        r = StudentRequest.query.get_or_404(request.form.get("request_id", type=int))
        status = request.form.get("status")
        if status in ("pending", "in_progress", "resolved", "rejected"):
            r.status = status
            r.handled_by = current_user.id
            _audit("request.update", "StudentRequest", r.id, status)
            db.session.commit()
            flash("Request updated.", "success")
        return redirect(url_for("teacher.requests_"))
    return render_template("requests.html",
                           requests=StudentRequest.query
                               .order_by(StudentRequest.created_at.desc()).all(),
                           mode="teacher")

def _notify(targetable, kind):
    students = visible_students(targetable)
    if kind == "notice":
        title = "New announcement: " + targetable.title
        link = url_for("student.notices")
    elif kind == "assignment":
        title = "New assignment: " + targetable.title
        link = url_for("student.assignments")
    elif kind == "timetable":
        title = "Timetable updated"
        link = url_for("student.timetable")
    else:
        title = "Update"
        link = url_for("dashboard")
    for s in students:
        db.session.add(Notification(user_id=s.user_id, kind=kind,
                                    title=title, link=link))
