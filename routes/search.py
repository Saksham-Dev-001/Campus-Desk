from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models import Student, Notice, Assignment, FileRecord, Subject
from services.targeting import apply_target_filter

search_bp = Blueprint("search", __name__)

HIDE = ("Official Timetable", "Announcement", "[CampusDesk]")

@search_bp.route("/search")
@login_required
def search():
    q = (request.args.get("q") or "").strip()
    results = {"notices": [], "assignments": [], "files": [], "subjects": []}
    if q:
        like = f"%{q}%"
        nq = Notice.query.filter(Notice.active == True, Notice.title.ilike(like))
        aq = Assignment.query.filter(Assignment.title.ilike(like))
        fq = FileRecord.query.filter(FileRecord.status == "active", FileRecord.filename.ilike(like))
        sq = Subject.query.filter(Subject.name.ilike(like))

        if current_user.is_student:
            s = Student.query.filter_by(user_id=current_user.id).first()
            if s:
                nq = apply_target_filter(nq, Notice, s)
                aq = apply_target_filter(aq, Assignment, s)
                fq = apply_target_filter(fq, FileRecord, s)
                for x in HIDE:
                    fq = fq.filter(~FileRecord.filename.ilike(x + "%"))
                if s.branch_id:
                    sq = sq.filter((Subject.branch_id == s.branch_id) | (Subject.branch_id.is_(None)))
                if s.semester_id:
                    sq = sq.filter((Subject.semester_id == s.semester_id) | (Subject.semester_id.is_(None)))

        results["notices"] = nq.limit(30).all()
        results["assignments"] = aq.limit(30).all()
        results["files"] = fq.limit(30).all()
        results["subjects"] = sq.limit(30).all()

    return render_template("search.html", q=q, results=results)
