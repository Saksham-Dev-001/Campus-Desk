"""JSON APIs - targeting + notifications + preview + folder tree."""
from datetime import datetime
from io import BytesIO
from flask import Blueprint, jsonify, request, abort, send_file, current_app
from flask_login import login_required, current_user

from models import (Branch, Section, Batch, Subject, Semester, Year, Course,
                    Notification, FileRecord, Student, User, Teacher, Folder,
                    Notice, Assignment)
from services.targeting import matches
from services.storage import get_storage_provider

api_bp = Blueprint("api", __name__, url_prefix="/api")

# ---------- Targeting dropdowns ----------
@api_bp.route("/courses")
@login_required
def courses():
    return jsonify([{"id": c.id, "name": c.name}
                    for c in Course.query.order_by(Course.name)])

@api_bp.route("/branches")
@login_required
def branches():
    cid = request.args.get("course_id", type=int)
    q = Branch.query
    if cid:
        q = q.filter(Branch.course_id == cid)
    return jsonify([{"id": b.id, "name": b.name, "code": b.code}
                    for b in q.order_by(Branch.code)])

@api_bp.route("/years")
@login_required
def years():
    return jsonify([{"id": y.id, "name": y.name}
                    for y in Year.query.order_by(Year.order_index)])

@api_bp.route("/semesters")
@login_required
def semesters():
    return jsonify([{"id": s.id, "name": s.name}
                    for s in Semester.query.order_by(Semester.order_index)])

@api_bp.route("/sections")
@login_required
def sections():
    bid = request.args.get("branch_id", type=int)
    yid = request.args.get("year_id", type=int)
    q = Section.query
    if bid:
        q = q.filter(Section.branch_id == bid)
    if yid:
        q = q.filter(Section.year_id == yid)
    return jsonify([{"id": s.id, "name": s.name}
                    for s in q.order_by(Section.name)])

@api_bp.route("/batches")
@login_required
def batches():
    sid = request.args.get("section_id", type=int)
    q = Batch.query
    if sid:
        q = q.filter(Batch.section_id == sid)
    return jsonify([{"id": b.id, "name": b.name}
                    for b in q.order_by(Batch.name)])

@api_bp.route("/subjects")
@login_required
def subjects():
    bid = request.args.get("branch_id", type=int)
    sid = request.args.get("semester_id", type=int)
    q = Subject.query
    if bid:
        q = q.filter((Subject.branch_id == bid) | (Subject.branch_id.is_(None)))
    if sid:
        q = q.filter((Subject.semester_id == sid) | (Subject.semester_id.is_(None)))
    return jsonify([{"id": s.id, "name": s.name}
                    for s in q.order_by(Subject.name)])

# ---------- Notification bell ----------
def _time_ago(dt):
    if not dt:
        return ""
    delta = datetime.utcnow() - dt
    s = int(delta.total_seconds())
    if s < 60:
        return "just now"
    if s < 3600:
        return "{}m ago".format(s // 60)
    if s < 86400:
        return "{}h ago".format(s // 3600)
    if s < 604800:
        return "{}d ago".format(s // 86400)
    return dt.strftime("%d %b")

@api_bp.route("/notifications/unread-count")
@login_required
def unread_count():
    n = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    return jsonify({"count": n})

@api_bp.route("/notifications/recent")
@login_required
def recent_notifications():
    limit = min(request.args.get("limit", 8, type=int) or 8, 30)
    items = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).limit(limit).all()
    return jsonify({"items": [{
        "id": n.id, "kind": n.kind, "title": n.title,
        "message": n.message or "", "link": n.link or "",
        "read": bool(n.read), "time_ago": _time_ago(n.created_at),
    } for n in items]})

@api_bp.route("/stats")
@login_required
def stats():
    return jsonify({
        "users": User.query.count(),
        "students": Student.query.count(),
        "teachers": Teacher.query.count(),
        "branches": Branch.query.count(),
        "files": FileRecord.query.count(),
        "folders": Folder.query.count(),
        "notices": Notice.query.filter_by(active=True).count(),
        "assignments": Assignment.query.count(),
    })

# ---------- Folder tree (for upload picker) ----------
@api_bp.route("/folders/tree")
@login_required
def folders_tree():
    """Return all folders the current user can upload into.

    Admins/global teachers: all folders.
    Teachers/student_admins: only their branches + NULL branch (common).
    Students: forbidden.
    """
    if current_user.is_student:
        abort(403)

    q = Folder.query
    if not current_user.is_admin:
        t = current_user.teacher if current_user.role == "teacher" else None
        is_global = t.is_global if t else False
        if not is_global:
            allowed = current_user.allowed_branch_ids()
            if allowed:
                from sqlalchemy import or_
                q = q.filter(or_(Folder.branch_id.is_(None),
                                 Folder.branch_id.in_(allowed)))
            else:
                q = q.filter(Folder.branch_id.is_(None))

    folders = q.all()
    if not current_user.is_admin and current_user.role == "teacher":
        t = current_user.teacher
        is_global = t.is_global if t else False
        if not is_global:
            allowed_subs = set(current_user.allowed_subject_ids())
            def _folder_allowed(f):
                curr = f
                while curr:
                    if curr.subject_id is not None:
                        return curr.subject_id in allowed_subs
                    curr = curr.parent
                return True
            folders = [f for f in folders if _folder_allowed(f)]

    # Build tree
    by_id = {}
    for f in folders:
        by_id[f.id] = {
            "id": f.id,
            "name": f.name,
            "parent_id": f.parent_id,
            "children": [],
        }
    roots = []
    for node in by_id.values():
        pid = node["parent_id"]
        if pid and pid in by_id:
            by_id[pid]["children"].append(node)
        else:
            roots.append(node)

    def sort_rec(items):
        items.sort(key=lambda x: x["name"].lower())
        for it in items:
            sort_rec(it["children"])

    sort_rec(roots)
    return jsonify({"tree": roots})

# ---------- Preview ----------
def _served_name(rec):
    name = (rec.filename or "").strip()
    orig = (rec.original_filename or "").strip()
    if "." not in name and "." in orig:
        ext = orig.rsplit(".", 1)[1].lower()
        if ext in current_app.config["ALLOWED_EXTENSIONS"]:
            return name + "." + ext
    return name or orig or "file"

def _effective_subject_id_api(item):
    if not item:
        return None
    if getattr(item, "subject_id", None):
        return item.subject_id
    curr = getattr(item, "folder", None)
    while curr:
        if getattr(curr, "subject_id", None):
            return curr.subject_id
        curr = getattr(curr, "parent", None)
    return None

def _serve_preview(fid):
    if not current_user.is_authenticated:
        abort(401)
    rec = FileRecord.query.get_or_404(fid)

    if current_user.is_student:
        s = Student.query.filter_by(user_id=current_user.id).first()
        if not s:
            abort(403)
        if not matches(s, rec):
            asg = Assignment.query.filter_by(attachment_file_id=rec.id).first()
            if not (asg and matches(s, asg)):
                abort(403)
    elif current_user.role in ("teacher", "student_admin"):
        if rec.uploaded_by != current_user.id:
            if not current_user.can_write_branch(rec.branch_id):
                asg = Assignment.query.filter_by(attachment_file_id=rec.id).first()
                if not (asg and (asg.created_by == current_user.id or current_user.can_write_branch(asg.branch_id))):
                    abort(403)
            if current_user.role == "teacher":
                t = getattr(current_user, "teacher", None)
                is_global = t.is_global if t else False
                if not is_global:
                    sub_id = _effective_subject_id_api(rec)
                    if sub_id is not None and not current_user.can_access_subject(sub_id):
                        abort(403)

    provider = get_storage_provider(current_app.config)
    try:
        data = provider.download_file(rec.storage_ref)
    except Exception as e:
        current_app.logger.warning("Preview download failed: %s", e)
        abort(404)

    return send_file(BytesIO(data),
                     mimetype=rec.mime_type or "application/octet-stream",
                     download_name=_served_name(rec),
                     as_attachment=False)

@api_bp.route("/files/<int:fid>/preview")
@login_required
def file_preview(fid):
    return _serve_preview(fid)
