"""Smart targeting engine — the CORE of CampusDesk.

A NULL target field means "applies to all".
A non-NULL field must equal the student's value for the row to be visible.
"""
from sqlalchemy import or_

TARGET_FIELDS = ("course_id", "branch_id", "year_id",
                 "semester_id", "section_id", "batch_id")

def target_clauses(model, student):
    clauses = []
    for field in TARGET_FIELDS:
        col = getattr(model, field)
        clauses.append(or_(col.is_(None), col == getattr(student, field)))
    return clauses

def apply_target_filter(query, model, student):
    for clause in target_clauses(model, student):
        query = query.filter(clause)
    return query

def matches(student, obj):
    for field in TARGET_FIELDS:
        v = getattr(obj, field, None)
        if v is not None and v != getattr(student, field, None):
            return False
    return True

def visible_students(model_row):
    from models import Student
    from sqlalchemy.orm import joinedload
    q = Student.query.options(joinedload(Student.user), joinedload(Student.section), joinedload(Student.batch), joinedload(Student.branch))
    for field in TARGET_FIELDS:
        v = getattr(model_row, field, None)
        if v is not None:
            q = q.filter(getattr(Student, field) == v)
    return q.all()

_target_name_cache = {}

def target_label(row):
    """Return a short human-readable target summary, e.g. 'CSE · 1st Year · Section A · A2'."""
    from models import Course, Branch, Year, Semester, Section, Batch, Subject
    parts = []
    pairs = [
        ("course_id", Course, lambda x: x.name),
        ("branch_id", Branch, lambda x: x.code),
        ("year_id", Year, lambda x: x.name),
        ("semester_id", Semester, lambda x: x.name),
        ("section_id", Section, lambda x: f"Section {x.name}"),
        ("batch_id", Batch, lambda x: x.name),
        ("subject_id", Subject, lambda x: x.name),
    ]
    for field, Model, getter in pairs:
        vid = getattr(row, field, None)
        if vid:
            cache_key = (Model.__tablename__, vid)
            if cache_key not in _target_name_cache:
                obj = Model.query.get(vid)
                _target_name_cache[cache_key] = getter(obj) if obj else None
            val = _target_name_cache[cache_key]
            if val:
                parts.append(val)
    return " · ".join(parts) if parts else "Everyone"

def enforce_teacher_scope(user, branch_id):
    """Raise 403 if the user may not write to this branch.

    Admin: always allowed.
    Teacher / student_admin: only if branch is in their allowed set.
    Any other role: never allowed.
    """
    from flask import abort
    if not user.is_authenticated:
        abort(403)
    if user.is_admin:
        return
    if user.role in ("teacher", "student_admin"):
        if not user.can_write_branch(branch_id):
            abort(403)
        return
    abort(403)

def parse_target_from_form(form):
    out = {}
    for field in TARGET_FIELDS + ("subject_id",):
        raw = form.get(field)
        if raw in (None, "", "all", "0"):
            out[field] = None
        else:
            try:
                out[field] = int(raw)
            except (TypeError, ValueError):
                out[field] = None
    return out
