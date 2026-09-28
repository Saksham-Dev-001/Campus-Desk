from datetime import datetime
from services.time_utils import now_ist
import hashlib
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if type(dbapi_connection).__module__ == "sqlite3":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160))
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=now_ist)

    student = db.relationship("Student", backref="user", uselist=False,
                              cascade="all, delete-orphan")
    teacher = db.relationship("Teacher", backref="user", uselist=False,
                              cascade="all, delete-orphan")

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def is_active(self):
        return bool(self.active)

    @property
    def is_student(self):
        return self.role in ("student", "student_admin")

    @property
    def is_teacher(self):
        return self.role == "teacher"

    @property
    def is_admin(self):
        return self.role == "admin"

    def allowed_branches(self):
        """Branches this user can WRITE to."""
        if self.is_admin:
            return Branch.query.order_by(Branch.code).all()
        if self.role == "teacher":
            t = self.teacher
            if t and t.is_global:
                return Branch.query.order_by(Branch.code).all()
            rows = TeacherBranch.query.filter_by(user_id=self.id).all()
            if rows:
                return [r.branch for r in rows if r.branch]
            if t and getattr(t, "branch_id", None):
                b = Branch.query.get(t.branch_id)
                return [b] if b else []
            return []
        if self.role == "student_admin":
            rows = TeacherBranch.query.filter_by(user_id=self.id).all()
            if rows:
                return [r.branch for r in rows if r.branch]
            s = self.student
            if s and s.branch:
                return [s.branch]
            return []
        return []

    def allowed_branch_ids(self):
        return [b.id for b in self.allowed_branches()]

    def can_write_branch(self, branch_id):
        """True if user may create/edit content for this branch."""
        if self.is_admin:
            return True
        if branch_id is None:
            if self.role == "teacher" and self.teacher and self.teacher.is_global:
                return True
            return False
        try:
            bid = int(branch_id)
        except (TypeError, ValueError):
            return False
        return bid in self.allowed_branch_ids()

    def allowed_subjects(self):
        """Subjects this user is assigned to teach."""
        if self.is_admin:
            return Subject.query.order_by(Subject.name).all()
        if self.role == "teacher":
            t = self.teacher
            if t and t.is_global:
                return Subject.query.order_by(Subject.name).all()
            rows = TeacherSubject.query.filter_by(user_id=self.id).all()
            subs = [r.subject for r in rows if r.subject]
            if not subs and t:
                # Fallback to timetable entries if not yet explicitly mapped
                sub_ids = [r[0] for r in db.session.query(TimetableEntry.subject_id).filter(
                    TimetableEntry.teacher_id == t.id,
                    TimetableEntry.subject_id.isnot(None)
                ).distinct().all()]
                if sub_ids:
                    subs = Subject.query.filter(Subject.id.in_(sub_ids)).order_by(Subject.name).all()
            unique = []
            seen = set()
            for s in subs:
                key = (s.code or "").strip().lower() or (s.name or "").strip().lower()
                if key not in seen:
                    seen.add(key)
                    unique.append(s)
            return unique
        return []

    def allowed_subject_ids(self):
        subs = self.allowed_subjects()
        if not subs:
            return []
        codes = {s.code for s in subs if s.code}
        names = {s.name.strip().lower() for s in subs if s.name}
        matching = Subject.query.filter(
            db.or_(
                Subject.id.in_([s.id for s in subs]),
                Subject.code.in_(codes),
                Subject.name.in_([s.name for s in subs])
            )
        ).all()
        return [s.id for s in matching]

    def can_access_subject(self, subject_id):
        if self.is_admin:
            return True
        if self.role == "teacher":
            t = self.teacher
            if t and t.is_global:
                return True
            if subject_id is None:
                return True
            try:
                sid = int(subject_id)
            except (TypeError, ValueError):
                return False
            return sid in self.allowed_subject_ids()
        return True

    @property
    def initials(self):
        parts = (self.name or "?").split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return (self.name or "??")[:2].upper()

    @property
    def avatar_color(self):
        h = int(hashlib.md5((self.name or "x").encode()).hexdigest()[:8], 16)
        colors = [
            ("#2b5cff", "#7c3aed"),
            ("#0891b2", "#3b82f6"),
            ("#059669", "#10b981"),
            ("#d97706", "#f59e0b"),
            ("#dc2626", "#ef4444"),
            ("#7c3aed", "#a855f7"),
            ("#db2777", "#ec4899"),
            ("#0f766e", "#14b8a6"),
        ]
        c1, c2 = colors[h % len(colors)]
        return "linear-gradient(135deg,{}, {})".format(c1, c2)

class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

class Branch(db.Model):
    __tablename__ = "branches"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    course = db.relationship("Course")

class Year(db.Model):
    __tablename__ = "years"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    order_index = db.Column(db.Integer, default=0)

class Semester(db.Model):
    __tablename__ = "semesters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    order_index = db.Column(db.Integer, default=0)

class Section(db.Model):
    __tablename__ = "sections"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    year_id = db.Column(db.Integer, db.ForeignKey("years.id"), nullable=False)
    branch = db.relationship("Branch")
    year = db.relationship("Year")
    __table_args__ = (db.UniqueConstraint("name", "branch_id", "year_id"),)

class Batch(db.Model):
    __tablename__ = "batches"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    section = db.relationship("Section")
    __table_args__ = (db.UniqueConstraint("name", "section_id"),)

class Subject(db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(40))
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"))
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"))
    branch = db.relationship("Branch")
    semester = db.relationship("Semester")

class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    enrollment_number = db.Column(db.String(60), unique=True, nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"))
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"))
    year_id = db.Column(db.Integer, db.ForeignKey("years.id"))
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"))
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"))
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"))

    course = db.relationship("Course")
    branch = db.relationship("Branch")
    year = db.relationship("Year")
    semester = db.relationship("Semester")
    section = db.relationship("Section")
    batch = db.relationship("Batch")

    @property
    def academic_label(self):
        parts = [
            self.course.name if self.course else None,
            self.branch.code if self.branch else None,
            self.year.name if self.year else None,
            self.semester.name if self.semester else None,
            f"Section {self.section.name}" if self.section else None,
            self.batch.name if self.batch else None,
        ]
        return " • ".join(p for p in parts if p)

    @property
    def short_label(self):
        parts = [
            self.branch.code if self.branch else None,
            self.year.name if self.year else None,
            f"Sec {self.section.name}" if self.section else None,
            self.batch.name if self.batch else None,
        ]
        return " · ".join(p for p in parts if p)

class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    teacher_id = db.Column(db.String(60), unique=True, nullable=False, index=True)
    department = db.Column(db.String(80))
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True)
    is_global = db.Column(db.Boolean, default=False, nullable=False)
    branch = db.relationship("Branch", foreign_keys=[branch_id])

class TeacherBranch(db.Model):
    """Mapping: which branches can a teacher / student_admin write to?"""
    __tablename__ = "teacher_branches"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    __table_args__ = (db.UniqueConstraint("user_id", "branch_id"),)
    user = db.relationship("User")
    branch = db.relationship("Branch")

class TeacherSubject(db.Model):
    """Mapping: which subjects is a teacher assigned to teach?"""
    __tablename__ = "teacher_subjects"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False, index=True)
    __table_args__ = (db.UniqueConstraint("user_id", "subject_id"),)
    user = db.relationship("User")
    subject = db.relationship("Subject")

def _target_columns():
    return dict(
        course_id=db.Column(db.Integer, db.ForeignKey("courses.id")),
        branch_id=db.Column(db.Integer, db.ForeignKey("branches.id")),
        year_id=db.Column(db.Integer, db.ForeignKey("years.id")),
        semester_id=db.Column(db.Integer, db.ForeignKey("semesters.id")),
        section_id=db.Column(db.Integer, db.ForeignKey("sections.id")),
        batch_id=db.Column(db.Integer, db.ForeignKey("batches.id")),
        subject_id=db.Column(db.Integer, db.ForeignKey("subjects.id")),
    )

class Folder(db.Model):
    __tablename__ = "folders"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("folders.id"))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now_ist)

    # FIX: cascade so deleting a parent auto-deletes children and files,
    # instead of orphaning them at the root.
    children = db.relationship(
        "Folder",
        backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        passive_deletes=False,
    )
    files = db.relationship(
        "FileRecord",
        backref="folder",
        cascade="all, delete-orphan",
    )

    course_id = _target_columns()["course_id"]
    branch_id = _target_columns()["branch_id"]
    year_id = _target_columns()["year_id"]
    semester_id = _target_columns()["semester_id"]
    section_id = _target_columns()["section_id"]
    batch_id = _target_columns()["batch_id"]
    subject_id = _target_columns()["subject_id"]

class FileRecord(db.Model):
    __tablename__ = "files"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(120))
    size_bytes = db.Column(db.Integer, default=0)
    folder_id = db.Column(db.Integer, db.ForeignKey("folders.id"))
    version = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default="active")
    storage_provider = db.Column(db.String(40), nullable=False)
    storage_ref = db.Column(db.Text, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=now_ist)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist)
    uploader = db.relationship("User", foreign_keys=[uploaded_by])
    course_id = _target_columns()["course_id"]
    branch_id = _target_columns()["branch_id"]
    year_id = _target_columns()["year_id"]
    semester_id = _target_columns()["semester_id"]
    section_id = _target_columns()["section_id"]
    batch_id = _target_columns()["batch_id"]
    subject_id = _target_columns()["subject_id"]

    @property
    def is_previewable(self):
        if not self.mime_type:
            return False
        return self.mime_type.startswith("image/") or self.mime_type == "application/pdf"

    @property
    def ext(self):
        if "." in (self.filename or ""):
            return self.filename.rsplit(".", 1)[1].lower()
        return ""

    @property
    def icon(self):
        e = self.ext
        if e == "pdf": return "📕"
        if e in ("doc", "docx"): return "📘"
        if e in ("xls", "xlsx", "csv"): return "📗"
        if e in ("ppt", "pptx"): return "📙"
        if e in ("png", "jpg", "jpeg", "webp", "gif"): return "🖼️"
        if e in ("zip", "rar", "7z"): return "🗜️"
        return "📄"

    @property
    def size_formatted(self):
        b = self.size_bytes or 0
        if b < 1024:
            return f"{b} B"
        elif b < 1024 * 1024:
            return f"{b / 1024:.1f} KB"
        else:
            return f"{b / (1024 * 1024):.1f} MB"

class FileVersion(db.Model):
    __tablename__ = "file_versions"
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    storage_ref = db.Column(db.Text, nullable=False)
    original_filename = db.Column(db.String(255))
    size_bytes = db.Column(db.Integer, default=0)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=now_ist)
    file = db.relationship("FileRecord",
                           backref=db.backref("versions", cascade="all, delete-orphan"))

class Notice(db.Model):
    __tablename__ = "notices"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default="normal")
    attachment_file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="SET NULL"))
    publish_date = db.Column(db.DateTime, default=now_ist)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    active = db.Column(db.Boolean, default=True)
    attachment = db.relationship("FileRecord")
    author = db.relationship("User", foreign_keys=[created_by])
    course_id = _target_columns()["course_id"]
    branch_id = _target_columns()["branch_id"]
    year_id = _target_columns()["year_id"]
    semester_id = _target_columns()["semester_id"]
    section_id = _target_columns()["section_id"]
    batch_id = _target_columns()["batch_id"]
    subject_id = _target_columns()["subject_id"]

class Assignment(db.Model):
    __tablename__ = "assignments"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    attachment_file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="SET NULL"))
    publish_date = db.Column(db.DateTime, default=now_ist)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="open")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    attachment = db.relationship("FileRecord")
    author = db.relationship("User", foreign_keys=[created_by])
    course_id = _target_columns()["course_id"]
    branch_id = _target_columns()["branch_id"]
    year_id = _target_columns()["year_id"]
    semester_id = _target_columns()["semester_id"]
    section_id = _target_columns()["section_id"]
    batch_id = _target_columns()["batch_id"]
    subject_id = _target_columns()["subject_id"]

    @property
    def subject(self):
        return Subject.query.get(self.subject_id) if self.subject_id else None

    @property
    def days_left(self):
        if not self.due_date:
            return None
        delta = (self.due_date - now_ist()).days
        return delta

    def submission_for(self, student):
        return AssignmentSubmission.query.filter_by(
            assignment_id=self.id, student_id=student.id
        ).first()

    def submission_count(self):
        return AssignmentSubmission.query.filter_by(assignment_id=self.id).count()

class AssignmentSubmission(db.Model):
    __tablename__ = "assignment_submissions"
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="SET NULL"))
    submitted_at = db.Column(db.DateTime, default=now_ist)
    status = db.Column(db.String(20), default="submitted")
    note = db.Column(db.Text)
    grade = db.Column(db.String(10))
    feedback = db.Column(db.Text)

    assignment = db.relationship("Assignment",
                                 backref=db.backref("submissions", cascade="all, delete-orphan"))
    student = db.relationship("Student")
    file = db.relationship("FileRecord")

class TimetableEntry(db.Model):
    __tablename__ = "timetable"
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    room = db.Column(db.String(40))
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    teacher = db.relationship("Teacher")
    course_id = _target_columns()["course_id"]
    branch_id = _target_columns()["branch_id"]
    year_id = _target_columns()["year_id"]
    semester_id = _target_columns()["semester_id"]
    section_id = _target_columns()["section_id"]
    batch_id = _target_columns()["batch_id"]
    subject_id = _target_columns()["subject_id"]

    branch = db.relationship("Branch", foreign_keys=[branch_id])
    section = db.relationship("Section", foreign_keys=[section_id])
    batch = db.relationship("Batch", foreign_keys=[batch_id])
    subject = db.relationship("Subject", foreign_keys=[subject_id])

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(255))
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now_ist)

class StudentRequest(db.Model):
    __tablename__ = "requests"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    subject = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    attachment_file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="SET NULL"))
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=now_ist)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist)
    handled_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    student = db.relationship("Student", backref="requests")
    attachment = db.relationship("FileRecord")
    handler = db.relationship("User", foreign_keys=[handled_by])

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(80), nullable=False)
    entity = db.Column(db.String(60))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now_ist)
    user = db.relationship("User")

class StorageMapping(db.Model):
    __tablename__ = "storage_mappings"
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, unique=True)
    provider = db.Column(db.String(40), default="local")
    config_json = db.Column(db.Text)
    branch = db.relationship("Branch")
