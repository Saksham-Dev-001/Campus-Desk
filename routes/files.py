from datetime import datetime
from services.time_utils import now_ist
from io import BytesIO
from urllib.parse import urlparse, urljoin
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, send_file, abort, current_app, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_

from models import (db, Folder, FileRecord, FileVersion, Student, Teacher, Branch, AuditLog,
                    Notice, Assignment, StudentRequest, AssignmentSubmission)
from services.targeting import (apply_target_filter, parse_target_from_form,
                                target_label, matches, enforce_teacher_scope)
from services.storage import get_storage_provider

files_bp = Blueprint("files", __name__)
HIDE = ("Official Timetable", "Announcement", "[CampusDesk]")

def _is_safe_redirect(target):
    if not target or not isinstance(target, str):
        return False
    if target.startswith("//") or target.startswith("\\\\"):
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc

def _safe_back(fallback="files.browse"):
    ref = request.referrer
    if ref and _is_safe_redirect(ref):
        return ref
    return url_for(fallback)

def _p():
    return get_storage_provider(current_app.config)

def _ok(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

def _mgr():
    if current_user.role not in ("teacher", "admin", "student_admin"):
        abort(403)

def _is_global_manager(user):
    """Admin or a teacher with is_global=True — can see everything."""
    if user.is_admin:
        return True
    if user.role == "teacher":
        t = user.teacher
        return bool(t and t.is_global)
    return False

def _filter_for_manager(query, model, user):
    """Restrict query on Folder/FileRecord to the branches a manager can see."""
    if _is_global_manager(user):
        return query
    allowed = user.allowed_branch_ids()
    if not allowed:
        return query.filter(getattr(model, "branch_id").is_(None))
    return query.filter(
        or_(
            getattr(model, "branch_id").is_(None),
            getattr(model, "branch_id").in_(allowed),
        )
    )

def _effective_subject_id(item):
    """Find the subject_id for a folder or file, checking itself or ancestor folders."""
    if not item:
        return None
    if getattr(item, "subject_id", None):
        return item.subject_id
    curr = getattr(item, "parent", None) if hasattr(item, "parent") else getattr(item, "folder", None)
    while curr:
        if getattr(curr, "subject_id", None):
            return curr.subject_id
        curr = getattr(curr, "parent", None)
    return None

def _can_see_folder(folder, user):
    if _is_global_manager(user):
        return True
    if folder is None:
        return True
    bid = folder.branch_id
    if bid is not None and bid not in user.allowed_branch_ids():
        return False
    if user.role == "teacher":
        sub_id = _effective_subject_id(folder)
        if sub_id is not None and not user.can_access_subject(sub_id):
            return False
    return True

def _can_manage_item(item):
    """Permission check for folder/file operations."""
    if not current_user.is_authenticated:
        return False

    if current_user.is_admin:
        return True

    bid = getattr(item, "branch_id", None)

    if current_user.role == "teacher":
        t = current_user.teacher
        if t and t.is_global:
            return True
        if bid is not None and not current_user.can_write_branch(bid):
            return False
        sub_id = _effective_subject_id(item)
        if sub_id is not None and not current_user.can_access_subject(sub_id):
            return False
        return True

    if current_user.role == "student_admin":
        if getattr(item, "created_by", None) == current_user.id or \
           getattr(item, "uploaded_by", None) == current_user.id:
            return True
        if not current_user.can_write_branch(bid):
            return False
        s = Student.query.filter_by(user_id=current_user.id).first()
        if not s:
            return False
        return matches(s, item)

    return False

def _clean_file_references(r):
    """Nullify FK references before deleting a file record."""
    if not r:
        return
    Notice.query.filter_by(attachment_file_id=r.id).update({"attachment_file_id": None})
    Assignment.query.filter_by(attachment_file_id=r.id).update({"attachment_file_id": None})
    StudentRequest.query.filter_by(attachment_file_id=r.id).update({"attachment_file_id": None})
    AssignmentSubmission.query.filter_by(file_id=r.id).update({"file_id": None})

def _aud(a, e=None, i=None, d=None):
    db.session.add(AuditLog(user_id=current_user.id, action=a,
                            entity=e, entity_id=i, details=d))

def _bcode(bid):
    if not bid:
        return None
    b = Branch.query.get(bid)
    return b.code if b else None

def _fpath(f):
    parts, c = [], f
    while c:
        parts.append(c.name)
        c = c.parent
    return " / ".join(reversed(parts))

def _sname(r):
    n = (r.filename or "").strip()
    o = (r.original_filename or "").strip()
    if "." not in n and "." in o:
        e = o.rsplit(".", 1)[1].lower()
        if e in current_app.config["ALLOWED_EXTENSIONS"]:
            return n + "." + e
    return n or o or "file"

def _hide(q):
    for x in HIDE:
        q = q.filter(~FileRecord.filename.ilike(x + "%"))
    return q

def _try_delete_storage(ref, excluding_file_id=None):
    """Best-effort storage delete. Never raises. Only deletes physical file if not shared by other records."""
    if not ref:
        return
    try:
        # Check if other active FileRecord or FileVersion references this storage_ref
        q_rec = FileRecord.query.filter(FileRecord.storage_ref == ref)
        if excluding_file_id:
            q_rec = q_rec.filter(FileRecord.id != excluding_file_id)
        if q_rec.first():
            return

        q_ver = FileVersion.query.filter(FileVersion.storage_ref == ref)
        if excluding_file_id:
            q_ver = q_ver.filter(FileVersion.file_id != excluding_file_id)
        if q_ver.first():
            return

        _p().delete_file(ref)
    except Exception as e:
        current_app.logger.warning("Storage delete failed for %s: %s", ref, e)

def _delete_file_full(r):
    """Remove storage, versions, FK refs, and the DB row. Commit happens by caller."""
    _try_delete_storage(r.storage_ref, excluding_file_id=r.id)
    for v in FileVersion.query.filter_by(file_id=r.id).all():
        if v.storage_ref and v.storage_ref != r.storage_ref:
            _try_delete_storage(v.storage_ref, excluding_file_id=r.id)
    FileVersion.query.filter_by(file_id=r.id).delete()
    _clean_file_references(r)
    db.session.delete(r)

def _delrec(f, c):
    for x in list(f.files):
        _delete_file_full(x)
        c["files"] += 1
    for x in list(f.children):
        _delrec(x, c)
    db.session.delete(f)
    c["folders"] += 1

def _get_allowed_root_branch_folders(user):
    """Return root branch folders that user has write/manage permission for."""
    if not user.is_authenticated or user.role not in ("teacher", "admin", "student_admin"):
        return []

    root_folders = Folder.query.filter(
        Folder.parent_id.is_(None),
        Folder.branch_id.isnot(None)
    ).order_by(Folder.name).all()

    if user.is_admin:
        return root_folders

    if user.role == "teacher":
        t = user.teacher
        if t and t.is_global:
            return root_folders
        allowed_bids = set(user.allowed_branch_ids())
        return [f for f in root_folders if f.branch_id in allowed_bids]

    if user.role == "student_admin":
        s = Student.query.filter_by(user_id=user.id).first()
        if s and s.branch_id:
            return [f for f in root_folders if f.branch_id == s.branch_id]

    return []

@files_bp.route("/files")
@login_required
def browse():
    fid = request.args.get("folder_id", type=int)
    cur = Folder.query.get(fid) if fid else None
    fq = Folder.query.filter(Folder.parent_id == (fid or None))
    flq = _hide(FileRecord.query.filter(FileRecord.folder_id == (fid or None),
                                        FileRecord.status == "active"))
    if current_user.is_student:
        s = Student.query.filter_by(user_id=current_user.id).first()
        if not s:
            abort(403)
        fq = apply_target_filter(fq, Folder, s)
        flq = apply_target_filter(flq, FileRecord, s)
    elif current_user.role in ("teacher", "student_admin"):
        if cur is not None and not _can_see_folder(cur, current_user):
            abort(403)
        fq = _filter_for_manager(fq, Folder, current_user)
        flq = _filter_for_manager(flq, FileRecord, current_user)
    folders = fq.order_by(Folder.name).all()
    files = flq.order_by(FileRecord.updated_at.desc()).all()

    if current_user.role == "teacher" and not _is_global_manager(current_user):
        allowed_sub_ids = set(current_user.allowed_subject_ids())
        folders = [
            f for f in folders
            if _effective_subject_id(f) is None or _effective_subject_id(f) in allowed_sub_ids
        ]
        files = [
            r for r in files
            if _effective_subject_id(r) is None or _effective_subject_id(r) in allowed_sub_ids
        ]

    crumbs, c = [], cur
    while c:
        crumbs.append(c)
        c = c.parent
    crumbs.reverse()
    cm = current_user.role in ("teacher", "admin", "student_admin")
    allowed_root_branch_folders = _get_allowed_root_branch_folders(current_user)
    branches_map = {b.id: b.code for b in Branch.query.all()}
    return render_template("files.html", current=cur, crumbs=crumbs,
                           folders=folders, files=files,
                           target_label=target_label, can_manage=cm,
                           can_manage_item=_can_manage_item,
                           allowed_root_branch_folders=allowed_root_branch_folders,
                           branches_map=branches_map)

@files_bp.route("/folders/create", methods=["POST"])
@login_required
def create_folder():
    _mgr()
    n = (request.form.get("name") or "").strip()
    if not n:
        flash("Folder name is required.", "error")
        return redirect(_safe_back())
    pid = request.form.get("parent_id", type=int) or None
    t = parse_target_from_form(request.form)
    if pid:
        p = Folder.query.get_or_404(pid)
        if not _can_manage_item(p):
            abort(403)
        for k, v in t.items():
            if v is None:
                t[k] = getattr(p, k, None)
    elif current_user.role == "student_admin":
        s = Student.query.filter_by(user_id=current_user.id).first()
        if s and s.branch_id:
            t["branch_id"] = s.branch_id

    if not current_user.is_admin:
        enforce_teacher_scope(current_user, t.get("branch_id"))

    db.session.add(Folder(name=n[:160], parent_id=pid,
                          created_by=current_user.id, **t))
    _aud("folder.create", "Folder", None, n)
    db.session.commit()
    flash("Folder '" + n + "' created.", "success")
    return redirect(url_for("files.browse", folder_id=pid or ""))

@files_bp.route("/folders/<int:fid>/rename", methods=["POST"])
@login_required
def rename_folder(fid):
    _mgr()
    f = Folder.query.get_or_404(fid)
    if not _can_manage_item(f):
        abort(403)
    n = (request.form.get("name") or "").strip()
    if n:
        f.name = n[:160]
        _aud("folder.rename", "Folder", fid, n)
        db.session.commit()
        flash("Folder renamed.", "success")
    return redirect(url_for("files.browse", folder_id=f.parent_id or ""))

@files_bp.route("/folders/<int:fid>/delete", methods=["POST"])
@login_required
def delete_folder(fid):
    _mgr()
    f = Folder.query.get_or_404(fid)
    if not _can_manage_item(f):
        abort(403)
    pid = f.parent_id
    c = {"folders": 0, "files": 0}
    _delrec(f, c)
    _aud("folder.delete", "Folder", fid, f.name)
    db.session.commit()
    flash("Deleted {} folder(s) and {} file(s).".format(c["folders"], c["files"]), "success")
    return redirect(url_for("files.browse", folder_id=pid or ""))

@files_bp.route("/files/upload", methods=["POST"])
@login_required
def upload_file():
    _mgr()
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please choose a file.", "error")
        return redirect(_safe_back())
    if not _ok(f.filename):
        flash("That file type is not allowed.", "error")
        return redirect(_safe_back())
    fid = request.form.get("folder_id", type=int) or None
    branch_folder_ids = request.form.getlist("branch_folder_ids", type=int)

    # Multi-branch folder upload at Root
    if not fid and branch_folder_ids:
        valid_targets = []
        for bfid in branch_folder_ids:
            bf = Folder.query.get(bfid)
            if bf and bf.parent_id is None and bf.branch_id is not None:
                if current_user.is_admin:
                    valid_targets.append(bf)
                elif current_user.role == "teacher":
                    t_user = current_user.teacher
                    if (t_user and t_user.is_global) or current_user.can_write_branch(bf.branch_id):
                        valid_targets.append(bf)
                elif current_user.role == "student_admin":
                    if current_user.can_write_branch(bf.branch_id):
                        valid_targets.append(bf)

        if not valid_targets:
            flash("No permitted branch folders selected.", "error")
            return redirect(_safe_back())

        t_common = parse_target_from_form(request.form)
        data = f.read()
        orig = secure_filename(f.filename) or "file"
        disp = (request.form.get("display_name") or orig).strip()[:255]
        if "." not in disp and "." in orig:
            e = orig.rsplit(".", 1)[1].lower()
            if e in current_app.config["ALLOWED_EXTENSIONS"]:
                disp = disp + "." + e

        p = _p()
        ref = p.upload_file(data, orig, branch_code=None, folder_path="Multi-Branch")
        prov_name = "local" if ref.startswith("local:") else p.name

        for tgt in valid_targets:
            tgt_data = dict(t_common)
            tgt_data["branch_id"] = tgt.branch_id
            rec = FileRecord(
                filename=disp,
                original_filename=orig,
                mime_type=f.mimetype,
                size_bytes=len(data),
                folder_id=tgt.id,
                storage_provider=prov_name,
                storage_ref=ref,
                uploaded_by=current_user.id,
                **tgt_data
            )
            db.session.add(rec)
            db.session.flush()
            db.session.add(FileVersion(
                file_id=rec.id,
                version=1,
                storage_ref=ref,
                original_filename=orig,
                size_bytes=len(data),
                uploaded_by=current_user.id
            ))
            _aud("file.upload", "FileRecord", rec.id, f"{disp} (multi-branch -> {tgt.name})")

        db.session.commit()
        b_names = [tgt.branch.code if tgt.branch else tgt.name for tgt in valid_targets]
        flash(f"Uploaded '{disp}' to {len(valid_targets)} branch folders ({', '.join(b_names)}).", "success")
        return redirect(url_for("files.browse"))

    folder = Folder.query.get(fid) if fid else None
    if folder and not _can_manage_item(folder):
        abort(403)
    t = parse_target_from_form(request.form)
    if folder:
        for k, v in t.items():
            if v is None:
                t[k] = getattr(folder, k, None)
    elif current_user.role == "student_admin":
        s = Student.query.filter_by(user_id=current_user.id).first()
        if s and s.branch_id:
            t["branch_id"] = s.branch_id

    if not current_user.is_admin:
        enforce_teacher_scope(current_user, t.get("branch_id"))

    data = f.read()
    orig = secure_filename(f.filename) or "file"
    disp = (request.form.get("display_name") or orig).strip()[:255]
    if "." not in disp and "." in orig:
        e = orig.rsplit(".", 1)[1].lower()
        if e in current_app.config["ALLOWED_EXTENSIONS"]:
            disp = disp + "." + e
    p = _p()
    ref = p.upload_file(data, orig, branch_code=_bcode(t.get("branch_id")),
                        folder_path=_fpath(folder) if folder else None)
    prov_name = "local" if ref.startswith("local:") else p.name
    rec = FileRecord(filename=disp, original_filename=orig, mime_type=f.mimetype,
                     size_bytes=len(data), folder_id=fid, storage_provider=prov_name,
                     storage_ref=ref, uploaded_by=current_user.id, **t)
    db.session.add(rec)
    db.session.flush()
    db.session.add(FileVersion(file_id=rec.id, version=1, storage_ref=ref,
                               original_filename=orig, size_bytes=len(data),
                               uploaded_by=current_user.id))
    _aud("file.upload", "FileRecord", rec.id, disp)
    db.session.commit()
    flash("Uploaded '" + disp + "'.", "success")
    return redirect(url_for("files.browse", folder_id=fid or ""))

@files_bp.route("/files/<int:fid>/replace", methods=["POST"])
@login_required
def replace_file(fid):
    _mgr()
    r = FileRecord.query.get_or_404(fid)
    if not _can_manage_item(r):
        abort(403)
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please choose a file.", "error")
        return redirect(_safe_back())
    if not _ok(f.filename):
        flash("That file type is not allowed.", "error")
        return redirect(_safe_back())
    data = f.read()
    orig = secure_filename(f.filename) or "file"
    p = _p()
    ref = p.replace_file(r.storage_ref, data, orig,
                         branch_code=_bcode(r.branch_id),
                         folder_path=_fpath(r.folder) if r.folder else None)
    r.storage_ref = ref
    r.storage_provider = "local" if ref.startswith("local:") else p.name
    r.original_filename = orig
    r.mime_type = f.mimetype
    r.size_bytes = len(data)
    r.version = (r.version or 1) + 1
    r.updated_at = now_ist()
    if "." not in (r.filename or "") and "." in orig:
        e = orig.rsplit(".", 1)[1].lower()
        if e in current_app.config["ALLOWED_EXTENSIONS"]:
            r.filename = r.filename + "." + e
    db.session.add(FileVersion(file_id=r.id, version=r.version, storage_ref=ref,
                               original_filename=orig, size_bytes=len(data),
                               uploaded_by=current_user.id))
    _aud("file.replace", "FileRecord", r.id, "v" + str(r.version))
    db.session.commit()
    flash("'" + r.filename + "' updated to v" + str(r.version) + ".", "success")
    return redirect(_safe_back())

@files_bp.route("/files/<int:fid>/rename", methods=["POST"])
@login_required
def rename_file(fid):
    _mgr()
    r = FileRecord.query.get_or_404(fid)
    if not _can_manage_item(r):
        abort(403)
    n = (request.form.get("filename") or "").strip()
    if n:
        if "." not in n and r.original_filename and "." in r.original_filename:
            e = r.original_filename.rsplit(".", 1)[1].lower()
            if e in current_app.config["ALLOWED_EXTENSIONS"]:
                n = n + "." + e
        r.filename = n[:255]
        _aud("file.rename", "FileRecord", fid, n)
        db.session.commit()
        flash("File renamed.", "success")
    return redirect(_safe_back())

@files_bp.route("/files/<int:fid>/delete", methods=["POST"])
@login_required
def delete_file(fid):
    """Delete file. Works even if the storage backend already lost it."""
    _mgr()
    r = FileRecord.query.get_or_404(fid)

    if not _can_manage_item(r):
        current_app.logger.warning(
            "Delete blocked for user=%s role=%s file=%s branch=%s",
            current_user.username, current_user.role, r.filename, r.branch_id
        )
        flash("You don't have permission to delete this file.", "error")
        return redirect(_safe_back())

    fname = r.filename
    _delete_file_full(r)
    _aud("file.delete", "FileRecord", fid, fname)
    try:
        db.session.commit()
        flash("File deleted.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Delete failed: %s", e)
        flash("Delete failed: " + str(e), "error")
    return redirect(_safe_back())

@files_bp.route("/bulk-delete", methods=["POST"])
@login_required
def bulk_delete():
    _mgr()
    data = request.get_json(silent=True) or {}
    fids = data.get("file_ids") or []
    folder_ids = data.get("folder_ids") or []
    c = {"files": 0, "folders": 0}
    for i in fids:
        r = FileRecord.query.get(i)
        if not r or not _can_manage_item(r):
            continue
        _delete_file_full(r)
        _aud("file.delete", "FileRecord", i, r.filename)
        c["files"] += 1
    for i in folder_ids:
        f = Folder.query.get(i)
        if not f or not _can_manage_item(f):
            continue
        _delrec(f, c)
        _aud("folder.delete", "Folder", i, f.name)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Bulk delete failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "deleted": c})

@files_bp.route("/files/<int:fid>/download")
@login_required
def download_file(fid):
    r = FileRecord.query.get_or_404(fid)
    if current_user.is_student:
        s = Student.query.filter_by(user_id=current_user.id).first()
        if not s:
            abort(403)
        if not matches(s, r):
            asg = Assignment.query.filter_by(attachment_file_id=r.id).first()
            if not (asg and matches(s, asg)):
                abort(403)
    elif current_user.role in ("teacher", "student_admin"):
        if r.uploaded_by != current_user.id:
            if not current_user.can_write_branch(r.branch_id):
                asg = Assignment.query.filter_by(attachment_file_id=r.id).first()
                if not (asg and (asg.created_by == current_user.id or current_user.can_write_branch(asg.branch_id))):
                    abort(403)
            if current_user.role == "teacher" and not _is_global_manager(current_user):
                sub_id = _effective_subject_id(r)
                if sub_id is not None and not current_user.can_access_subject(sub_id):
                    abort(403)
    try:
        data = _p().download_file(r.storage_ref)
    except Exception as e:
        current_app.logger.warning("Download failed for file %s: %s", fid, e)
        abort(404)
    return send_file(BytesIO(data), as_attachment=True,
                     download_name=_sname(r),
                     mimetype=r.mime_type or "application/octet-stream")
