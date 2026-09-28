"""Admin routes — users, structure, import, storage, audit log."""
import csv
import io
import json
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, current_app, send_file)
from flask_login import login_required, current_user

from models import (db, User, Student, Teacher, Course, Branch, Year, Semester,
                    Section, Batch, Subject, AuditLog, StorageMapping, Notice,
                    Assignment, FileRecord, StudentRequest, TeacherBranch, TeacherSubject)
from services.storage import get_storage_provider, TelegramProvider

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def _require_admin():
    if not current_user.is_admin:
        abort(403)

def _audit(action, entity=None, eid=None, details=None):
    db.session.add(AuditLog(user_id=current_user.id, action=action,
                            entity=entity, entity_id=eid, details=details))

@admin_bp.route("")
@admin_bp.route("/")
@login_required
def index():
    _require_admin()
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    _require_admin()
    stats = {
        "users": User.query.count(),
        "students": Student.query.count(),
        "teachers": Teacher.query.count(),
        "branches": Branch.query.count(),
        "notices": Notice.query.filter_by(active=True).count(),
        "assignments": Assignment.query.count(),
        "files": FileRecord.query.count(),
        "requests": StudentRequest.query.filter_by(status="pending").count(),
    }
    return render_template("dashboard_admin.html", stats=stats,
                           recent_audit=AuditLog.query
                               .order_by(AuditLog.created_at.desc()).limit(10).all(),
                           provider=get_storage_provider(current_app.config).name)

@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
def users():
    _require_admin()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create_teacher":
            username = (request.form.get("username") or "").strip()
            name = (request.form.get("name") or "").strip()
            password = request.form.get("password") or ""
            tid = (request.form.get("teacher_id") or username).strip()
            dept = (request.form.get("department") or "").strip()
            if not (username and name and password):
                flash("All fields are required.", "error")
            elif len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
            elif User.query.filter_by(username=username).first():
                flash("Username already exists.", "error")
            else:
                u = User(username=username, role="teacher", name=name)
                u.set_password(password)
                db.session.add(u)
                db.session.flush()

                # ---- Branch access from the Add Teacher modal ----
                is_global = request.form.get("is_global") == "1"
                branch_ids = request.form.getlist("branch_ids")

                t_obj = Teacher(user_id=u.id, teacher_id=tid,
                                department=dept, is_global=is_global)
                db.session.add(t_obj)
                db.session.flush()

                if not is_global:
                    for bid in branch_ids:
                        try:
                            bid = int(bid)
                        except (TypeError, ValueError):
                            continue
                        db.session.add(TeacherBranch(user_id=u.id, branch_id=bid))

                _audit("user.create", "User", u.id, "teacher " + username +
                       (" [global]" if is_global else " [{} branches]".format(len(branch_ids))))
                db.session.commit()
                flash("Teacher created successfully.", "success")
        elif action == "toggle_active":
            u = User.query.get(request.form.get("user_id", type=int))
            if u and u.id != current_user.id:
                u.active = not u.active
                _audit("user.toggle", "User", u.id, str(u.active))
                db.session.commit()
                flash("User status updated.", "success")
        elif action == "promote_sa":
            u = User.query.get(request.form.get("user_id", type=int))
            if u and u.is_student:
                u.role = "student_admin" if u.role == "student" else "student"
                _audit("user.role", "User", u.id, u.role)
                db.session.commit()
                flash("Role updated.", "success")
        elif action == "delete_teacher":
            tid = request.form.get("teacher_id", type=int)
            t = Teacher.query.get(tid)
            if t:
                u = t.user
                _audit("user.delete", "User", u.id if u else None, "teacher " + (u.username if u else str(tid)))
                TeacherBranch.query.filter_by(user_id=u.id).delete() if u else None
                db.session.delete(t)
                if u:
                    db.session.delete(u)
                db.session.commit()
                flash("Teacher deleted successfully.", "success")
        elif action == "assign_branch":
            tid = request.form.get("teacher_id", type=int)
            t = Teacher.query.get(tid)
            if t:
                branch_id = request.form.get("branch_id", type=int) or None
                b = Branch.query.get(branch_id) if branch_id else None
                t.branch_id = branch_id
                if b and not t.department:
                    t.department = b.code
                _audit("teacher.branch", "Teacher", t.id, f"branch_id={branch_id}")
                db.session.commit()
                flash("Teacher branch access updated successfully.", "success")
        return redirect(url_for("admin.users"))

    distinct_subjects = []
    seen_codes = set()
    for s in Subject.query.order_by(Subject.name).all():
        key = s.code or s.name
        if key not in seen_codes:
            seen_codes.add(key)
            distinct_subjects.append(s)

    return render_template("admin_users.html",
                           teachers=Teacher.query.all(),
                           student_admins=User.query.filter_by(role="student_admin").all(),
                           students=Student.query.order_by(Student.enrollment_number).all(),
                           all_branches_for_admin=Branch.query.order_by(Branch.code).all(),
                           branches=Branch.query.order_by(Branch.code).all(),
                           all_subjects_for_admin=distinct_subjects)

@admin_bp.route("/teachers/<int:uid>/branches", methods=["POST"])
@login_required
def teacher_branches(uid):
    """Assign write-access branches to a teacher / student_admin."""
    _require_admin()
    u = User.query.get_or_404(uid)
    if u.role not in ("teacher", "student_admin"):
        flash("Only teachers and student admins can have branch access.", "error")
        return redirect(url_for("admin.users"))

    is_global = request.form.get("is_global") == "1"
    branch_ids = request.form.getlist("branch_ids")

    if u.role == "teacher" and u.teacher:
        u.teacher.is_global = is_global

    TeacherBranch.query.filter_by(user_id=u.id).delete()
    if not is_global:
        for bid in branch_ids:
            try:
                bid = int(bid)
            except (TypeError, ValueError):
                continue
            db.session.add(TeacherBranch(user_id=u.id, branch_id=bid))

    _audit("user.branches", "User", u.id,
           "global" if is_global else "branches:" + ",".join(branch_ids))
    db.session.commit()
    flash(u.name + " — branch access updated.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/teachers/<int:uid>/subjects", methods=["POST"])
@login_required
def teacher_subjects(uid):
    """Assign subjects to a teacher."""
    _require_admin()
    u = User.query.get_or_404(uid)
    if u.role not in ("teacher", "student_admin"):
        flash("Only teachers and student admins can have subject assignments.", "error")
        return redirect(url_for("admin.users"))

    subject_ids = request.form.getlist("subject_ids")
    TeacherSubject.query.filter_by(user_id=u.id).delete()
    for sid in subject_ids:
        try:
            sid = int(sid)
        except (TypeError, ValueError):
            continue
        sub = Subject.query.get(sid)
        if sub and sub.code:
            matching_subs = Subject.query.filter_by(code=sub.code).all()
            for ms in matching_subs:
                if not TeacherSubject.query.filter_by(user_id=u.id, subject_id=ms.id).first():
                    db.session.add(TeacherSubject(user_id=u.id, subject_id=ms.id))
        else:
            db.session.add(TeacherSubject(user_id=u.id, subject_id=sid))

    _audit("user.subjects", "User", u.id, "subjects:" + ",".join(subject_ids))
    db.session.commit()
    flash(u.name + " — assigned subjects updated successfully.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/teachers/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_teachers():
    _require_admin()
    data = request.get_json(silent=True) or {}
    uids = data.get("user_ids") or []
    deleted = 0
    skipped = 0
    for uid in uids:
        try:
            uid = int(uid)
        except (TypeError, ValueError):
            continue
        if uid == current_user.id:
            skipped += 1
            continue
        u = User.query.get(uid)
        if not u or u.role != "teacher":
            skipped += 1
            continue
        try:
            TeacherBranch.query.filter_by(user_id=u.id).delete()
            Notice.query.filter_by(created_by=u.id).update({"created_by": None})
            Assignment.query.filter_by(created_by=u.id).update({"created_by": None})
            FileRecord.query.filter_by(uploaded_by=u.id).update({"uploaded_by": None})
            AuditLog.query.filter_by(user_id=u.id).update({"user_id": None})
            if u.teacher:
                db.session.delete(u.teacher)
                db.session.flush()
            db.session.delete(u)
            deleted += 1
        except Exception:
            db.session.rollback()
    if deleted:
        try:
            _audit("user.bulk_delete", "User", None, "deleted %d teacher(s)" % deleted)
            db.session.commit()
        except Exception:
            db.session.rollback()
    msg = "Deleted %d teacher(s)" % deleted
    if skipped:
        msg += " | %d skipped" % skipped
    from flask import jsonify
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"ok": True, "deleted": deleted, "skipped": skipped, "message": msg})
    flash(msg, "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/export/users.csv")
@login_required
def export_users_csv():
    _require_admin()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Username", "Name", "Role", "Active", "Created At"])
    for u in User.query.order_by(User.id).all():
        writer.writerow([u.id, u.username, u.name, u.role, u.active, u.created_at.isoformat() if u.created_at else ""])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                     mimetype="text/csv", as_attachment=True,
                     download_name="users.csv")

@admin_bp.route("/export/students.csv")
@login_required
def export_students_csv():
    _require_admin()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Enrollment Number", "Name", "Course", "Branch", "Year", "Semester", "Section", "Batch"])
    for s in Student.query.join(User).order_by(Student.enrollment_number).all():
        writer.writerow([
            s.enrollment_number,
            s.user.name if s.user else "",
            s.course.name if s.course else "",
            s.branch.code if s.branch else "",
            s.year.name if s.year else "",
            s.semester.name if s.semester else "",
            s.section.name if s.section else "",
            s.batch.name if s.batch else ""
        ])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                     mimetype="text/csv", as_attachment=True,
                     download_name="students.csv")

@admin_bp.route("/structure", methods=["GET", "POST"])
@login_required
def structure():
    _require_admin()
    if request.method == "POST":
        action = request.form.get("action", "add")
        kind = request.form.get("kind")
        name = (request.form.get("name") or "").strip()
        code = (request.form.get("code") or "").strip()
        item_id = request.form.get("item_id", type=int)

        model_map = {
            "course": Course,
            "branch": Branch,
            "year": Year,
            "semester": Semester,
            "section": Section,
            "batch": Batch,
            "subject": Subject,
        }

        try:
            if action == "delete":
                cls = model_map.get(kind)
                if not cls or not item_id:
                    flash("Invalid item for deletion.", "error")
                    return redirect(url_for("admin.structure"))
                obj = cls.query.get(item_id)
                if not obj:
                    flash("Item not found.", "error")
                    return redirect(url_for("admin.structure"))

                obj_name = getattr(obj, "name", str(item_id))

                # Safe nullification / dependent cascade
                if kind == "course":
                    Branch.query.filter_by(course_id=item_id).update({"course_id": None})
                    Student.query.filter_by(course_id=item_id).update({"course_id": None})
                elif kind == "branch":
                    TeacherBranch.query.filter_by(branch_id=item_id).delete()
                    Teacher.query.filter_by(branch_id=item_id).update({"branch_id": None})
                    Student.query.filter_by(branch_id=item_id).update({"branch_id": None})
                    Section.query.filter_by(branch_id=item_id).update({"branch_id": None})
                    Subject.query.filter_by(branch_id=item_id).update({"branch_id": None})
                    TimetableEntry.query.filter_by(branch_id=item_id).update({"branch_id": None})
                elif kind == "year":
                    Student.query.filter_by(year_id=item_id).update({"year_id": None})
                    Section.query.filter_by(year_id=item_id).update({"year_id": None})
                    TimetableEntry.query.filter_by(year_id=item_id).update({"year_id": None})
                elif kind == "semester":
                    Student.query.filter_by(semester_id=item_id).update({"semester_id": None})
                    Subject.query.filter_by(semester_id=item_id).update({"semester_id": None})
                    TimetableEntry.query.filter_by(semester_id=item_id).update({"semester_id": None})
                elif kind == "section":
                    Batch.query.filter_by(section_id=item_id).update({"section_id": None})
                    Student.query.filter_by(section_id=item_id).update({"section_id": None})
                    TimetableEntry.query.filter_by(section_id=item_id).update({"section_id": None})
                elif kind == "batch":
                    Student.query.filter_by(batch_id=item_id).update({"batch_id": None})
                    TimetableEntry.query.filter_by(batch_id=item_id).update({"batch_id": None})
                elif kind == "subject":
                    TeacherSubject.query.filter_by(subject_id=item_id).delete()
                    TimetableEntry.query.filter_by(subject_id=item_id).update({"subject_id": None})

                db.session.delete(obj)
                _audit("structure.delete", kind, item_id, details=obj_name)
                db.session.commit()
                cache.delete("timetable_grid")
                flash(f"{kind.title()} '{obj_name}' deleted.", "success")

            elif action == "edit":
                cls = model_map.get(kind)
                if not cls or not item_id:
                    flash("Invalid item for editing.", "error")
                    return redirect(url_for("admin.structure"))
                obj = cls.query.get(item_id)
                if not obj:
                    flash("Item not found.", "error")
                    return redirect(url_for("admin.structure"))

                if kind == "course" and name:
                    obj.name = name
                elif kind == "branch" and name and code:
                    obj.name = name
                    obj.code = code.upper()
                    cid = request.form.get("course_id", type=int)
                    if cid:
                        obj.course_id = cid
                elif kind == "year" and name:
                    obj.name = name
                    if request.form.get("order_index") is not None:
                        obj.order_index = request.form.get("order_index", type=int) or 0
                elif kind == "semester" and name:
                    obj.name = name
                    if request.form.get("order_index") is not None:
                        obj.order_index = request.form.get("order_index", type=int) or 0
                elif kind == "section" and name:
                    obj.name = name
                    bid = request.form.get("branch_id", type=int)
                    yid = request.form.get("year_id", type=int)
                    if bid: obj.branch_id = bid
                    if yid: obj.year_id = yid
                elif kind == "batch" and name:
                    obj.name = name
                    sid = request.form.get("section_id", type=int)
                    if sid: obj.section_id = sid
                elif kind == "subject" and name:
                    obj.name = name
                    obj.code = code or None
                    bid = request.form.get("branch_id", type=int)
                    sid = request.form.get("semester_id", type=int)
                    if bid: obj.branch_id = bid
                    if sid: obj.semester_id = sid

                _audit("structure.edit", kind, item_id, details=name)
                db.session.commit()
                cache.delete("timetable_grid")
                flash(f"{kind.title()} '{name}' updated successfully.", "success")

            else:
                # Add / create
                if kind == "course" and name:
                    db.session.add(Course(name=name))
                elif kind == "branch" and name and code:
                    db.session.add(Branch(name=name, code=code.upper(),
                                          course_id=request.form.get("course_id", type=int)))
                elif kind == "year" and name:
                    db.session.add(Year(name=name,
                                        order_index=request.form.get("order_index", type=int) or 0))
                elif kind == "semester" and name:
                    db.session.add(Semester(name=name,
                                            order_index=request.form.get("order_index", type=int) or 0))
                elif kind == "section" and name:
                    db.session.add(Section(name=name,
                                           branch_id=request.form.get("branch_id", type=int),
                                           year_id=request.form.get("year_id", type=int)))
                elif kind == "batch" and name:
                    db.session.add(Batch(name=name,
                                         section_id=request.form.get("section_id", type=int)))
                elif kind == "subject" and name:
                    db.session.add(Subject(name=name, code=code or None,
                                           branch_id=request.form.get("branch_id", type=int),
                                           semester_id=request.form.get("semester_id", type=int)))
                _audit("structure.create", kind, details=name)
                db.session.commit()
                cache.delete("timetable_grid")
                flash(kind.title() + " added.", "success")
        except Exception as e:
            db.session.rollback()
            flash("Error: " + str(e), "error")
        return redirect(url_for("admin.structure"))

    return render_template("admin_structure.html",
                           courses=Course.query.all(),
                           branches=Branch.query.all(),
                           years=Year.query.order_by(Year.order_index).all(),
                           semesters=Semester.query.order_by(Semester.order_index).all(),
                           sections=Section.query.all(),
                           batches=Batch.query.all(),
                           subjects=Subject.query.all())

@admin_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_students():
    _require_admin()
    report = None
    if request.method == "POST":
        f = request.files.get("csv")
        if not f:
            flash("Please choose a CSV file.", "error")
            return redirect(url_for("admin.import_students"))
        try:
            text = f.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            created, updated, errors = 0, 0, []
            for i, row in enumerate(reader, start=2):
                try:
                    is_new = _upsert_student(row)
                    if is_new:
                        created += 1
                    else:
                        updated += 1
                except Exception as e:
                    errors.append("Row " + str(i) + ": " + str(e))
            db.session.commit()
            report = {"created": created, "updated": updated, "errors": errors}
            _audit("student.import",
                   details=str(created) + " created, " + str(updated) + " updated")
            flash("Import complete - " + str(created) + " created, " +
                  str(updated) + " updated.", "success")
        except Exception as e:
            db.session.rollback()
            flash("Import failed: " + str(e), "error")
    return render_template("admin_import.html", report=report)

def _clean_csv(val):
    if not val:
        return ""
    s = str(val).strip()
    if s.startswith(("=", "+", "-", "@")):
        s = s.lstrip("=+-@").strip()
    return s

def _upsert_student(row):
    name = _clean_csv(row.get("name"))
    enroll = _clean_csv(row.get("enrollment_number"))
    if not name or not enroll:
        raise ValueError("name and enrollment_number are required")

    course_name = _clean_csv(row.get("course")) or "B.Tech"
    branch_code = _clean_csv(row.get("branch")).upper()
    year_name = _clean_csv(row.get("year")) or "1st Year"
    sem_name = _clean_csv(row.get("semester")) or "Sem 1"
    sec_name = _clean_csv(row.get("section")) or "A"
    batch_name = _clean_csv(row.get("batch")) or "A1"
    password = (row.get("password") or "password123").strip()

    course = Course.query.filter_by(name=course_name).first() or Course(name=course_name)
    db.session.add(course)
    db.session.flush()

    branch = Branch.query.filter_by(code=branch_code).first()
    if not branch:
        branch = Branch(name=branch_code, code=branch_code, course_id=course.id)
        db.session.add(branch)
        db.session.flush()

    year = Year.query.filter_by(name=year_name).first()
    if not year:
        year = Year(name=year_name, order_index=1)
        db.session.add(year)
        db.session.flush()

    sem = Semester.query.filter_by(name=sem_name).first()
    if not sem:
        sem = Semester(name=sem_name, order_index=1)
        db.session.add(sem)
        db.session.flush()

    section = Section.query.filter_by(name=sec_name, branch_id=branch.id,
                                      year_id=year.id).first()
    if not section:
        section = Section(name=sec_name, branch_id=branch.id, year_id=year.id)
        db.session.add(section)
        db.session.flush()

    batch = Batch.query.filter_by(name=batch_name, section_id=section.id).first()
    if not batch:
        batch = Batch(name=batch_name, section_id=section.id)
        db.session.add(batch)
        db.session.flush()

    user = User.query.filter_by(username=enroll).first()
    is_new = user is None
    if user:
        user.name = name
    else:
        user = User(username=enroll, role="student", name=name)
        u_set_password_safe(user, password)
        db.session.add(user)
        db.session.flush()

    student = Student.query.filter_by(enrollment_number=enroll).first()
    if not student:
        student = Student(user_id=user.id, enrollment_number=enroll)
        db.session.add(student)

    student.course_id = course.id
    student.branch_id = branch.id
    student.year_id = year.id
    student.semester_id = sem.id
    student.section_id = section.id
    student.batch_id = batch.id
    db.session.flush()
    return is_new

def u_set_password_safe(user, password):
    try:
        user.set_password(password)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# STORAGE — topic-based mapping (branch code → topic id)
# ---------------------------------------------------------------------------
@admin_bp.route("/storage", methods=["GET", "POST"])
@login_required
def storage():
    _require_admin()

    if request.method == "POST":
        action = request.form.get("action") or "map"

        if action == "map":
            branch_code = (request.form.get("branch_code") or "").strip().upper()
            topic_id = (request.form.get("topic_id") or "").strip()
            if not branch_code:
                flash("Branch code is required.", "error")
            else:
                _update_topics_env(branch_code, topic_id)
                _audit("storage.map", "Branch", None,
                       branch_code + " → " + (topic_id or "General"))
                flash("Topic mapping saved for " + branch_code + ".", "success")
            return redirect(url_for("admin.storage"))

        if action == "backup_db":
            provider = get_storage_provider(current_app.config)
            from pathlib import Path
            db_path = Path(current_app.instance_path) / "campusdesk.db"
            if not db_path.exists():
                db_path = Path(current_app.root_path) / "campusdesk.db"
            res = provider.backup_database(str(db_path))
            if res.get("ok"):
                _audit("database.backup", "Database", None, "Backed up to Telegram")
                flash("Database snapshot uploaded directly to Telegram Cloud successfully!", "success")
            else:
                flash("Database backup failed: " + str(res.get("error")), "error")
            return redirect(url_for("admin.storage"))

        if action == "test":
            provider = get_storage_provider(current_app.config)
            if isinstance(provider, TelegramProvider):
                me = provider.get_me()
                chat = provider.get_chat()
                if me.get("ok"):
                    flash("Bot OK: @" + me["result"].get("username", "?"), "success")
                else:
                    flash("Bot test failed: " + str(me.get("error") or me), "error")
                if chat.get("ok"):
                    flash("Chat OK: " + chat["result"].get("title", "?"), "success")
                else:
                    flash("Chat test failed: " + str(chat.get("error") or chat), "error")
            else:
                flash("Storage provider is 'local'. Set STORAGE_PROVIDER=telegram to test.", "info")
            return redirect(url_for("admin.storage"))

    provider = get_storage_provider(current_app.config)
    provider_name = provider.name
    topics = getattr(provider, "topics", {}) if isinstance(provider, TelegramProvider) else {}
    chat_id = getattr(provider, "chat_id", "") if isinstance(provider, TelegramProvider) else ""
    bot_username = ""
    if isinstance(provider, TelegramProvider):
        try:
            me = provider.get_me()
            if me.get("ok"):
                bot_username = me["result"].get("username", "")
        except Exception:
            pass

    branches = Branch.query.order_by(Branch.code).all()
    return render_template("admin_storage.html",
                           provider_name=provider_name,
                           branches=branches,
                           topics=topics,
                           chat_id=chat_id,
                           bot_username=bot_username,
                           configured=bool(provider_name == "telegram" and chat_id))

def _update_topics_env(branch_code: str, topic_id: str):
    """Save topic mapping to .env file (best-effort — also applies at runtime)."""
    try:
        from config import Config
        cfg = current_app.config
        try:
            topics = json.loads(cfg.get("TELEGRAM_TOPICS") or "{}")
        except json.JSONDecodeError:
            topics = {}
        if topic_id:
            try:
                topics[branch_code.upper()] = int(topic_id)
            except ValueError:
                flash("Topic ID must be a number.", "error")
                return
        else:
            topics.pop(branch_code.upper(), None)

        new_json = json.dumps(topics, separators=(",", ":"))
        cfg["TELEGRAM_TOPICS"] = new_json

        # Persist to .env so it survives a restart
        from pathlib import Path
        env_path = Path(current_app.root_path) / ".env"
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            out, found = [], False
            for line in lines:
                if line.startswith("TELEGRAM_TOPICS="):
                    out.append("TELEGRAM_TOPICS=" + new_json)
                    found = True
                else:
                    out.append(line)
            if not found:
                out.append("TELEGRAM_TOPICS=" + new_json)
            env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    except Exception as e:
        try:
            flash("Could not persist topic mapping: " + str(e), "error")
        except Exception:
            pass

# ---------------------------------------------------------------------------
# AUDIT LOG
# ---------------------------------------------------------------------------
@admin_bp.route("/audit")
@login_required
def audit():
    _require_admin()

    q_text = (request.args.get("q") or "").strip()
    action_filter = (request.args.get("action") or "").strip()
    user_filter = (request.args.get("user_id") or "").strip()

    query = AuditLog.query

    if q_text:
        like = "%" + q_text + "%"
        query = query.filter(
            db.or_(
                AuditLog.details.ilike(like),
                AuditLog.action.ilike(like),
                AuditLog.entity.ilike(like),
            )
        )
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    if user_filter:
        try:
            query = query.filter(AuditLog.user_id == int(user_filter))
        except (TypeError, ValueError):
            pass

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).limit(200).all()

    grouped = {}
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)

    for l in logs:
        d = l.created_at.date()
        if d == today:
            key = "Today"
        elif d == yesterday:
            key = "Yesterday"
        else:
            key = d.strftime("%d %B %Y")
        grouped.setdefault(key, []).append(l)

    today_count = AuditLog.query.filter(
        AuditLog.created_at >= datetime.combine(today, datetime.min.time())
    ).count()

    unique_users = db.session.query(db.func.count(db.distinct(AuditLog.user_id))) \
        .filter(AuditLog.user_id.isnot(None)).scalar() or 0

    delete_count = AuditLog.query.filter(AuditLog.action.ilike("%delete%")).count()

    action_options = [row[0] for row in db.session.query(AuditLog.action)
                      .distinct().order_by(AuditLog.action).all()]
    user_options = User.query.filter(
        User.id.in_(db.session.query(AuditLog.user_id).distinct())
    ).order_by(User.name).all()

    filters = {"q": q_text, "action": action_filter, "user_id": user_filter}

    return render_template(
        "admin_audit.html",
        logs=logs, grouped=grouped, total=total,
        today_count=today_count, unique_users=unique_users,
        delete_count=delete_count,
        action_options=action_options, user_options=user_options,
        filters=filters,
    )
