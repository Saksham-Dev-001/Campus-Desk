"""CampusDesk - app factory + blueprint wiring (v2.4).

v2.4 change: preview view is registered at BOTH endpoint names so
templates can use either `url_for('file_preview', ...)` OR
`url_for('api.file_preview', ...)` without breaking.
"""
import os
from flask import Flask, redirect, url_for, render_template, send_from_directory
from flask_login import current_user, login_required

from config import Config
from models import db, User
from extensions import login_manager, csrf, cache

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    db.init_app(app)
    # On Vercel the filesystem is read-only outside /tmp — creating the
    # upload folder may fail. That's fine since we use Telegram storage.
    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    except OSError:
        pass

    csrf.init_app(app)
    cache.init_app(app, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300})

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(uid):
        try:
            return db.session.get(User, int(uid))
        except Exception:
            return None

    # Inject targeting lookups into every template with eager loading (prevents N+1 queries)
    @app.context_processor
    def inject_target_lookups():
        try:
            from models import (Course, Branch, Year, Semester, Section,
                                Batch, Subject)
            from sqlalchemy.orm import joinedload
            return {
                "all_courses":   Course.query.order_by(Course.name).all(),
                "all_branches":  Branch.query.order_by(Branch.code).all(),
                "all_years":     Year.query.order_by(Year.order_index).all(),
                "all_semesters": Semester.query.order_by(Semester.order_index).all(),
                "all_sections":  Section.query.options(joinedload(Section.branch), joinedload(Section.year)).order_by(Section.name).all(),
                "all_batches":   Batch.query.options(joinedload(Batch.section)).order_by(Batch.name).all(),
                "all_subjects":  Subject.query.order_by(Subject.name).all(),
            }
        except Exception:
            return {
                "all_courses": [], "all_branches": [], "all_years": [],
                "all_semesters": [], "all_sections": [], "all_batches": [],
                "all_subjects": [],
            }

    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.teacher import teacher_bp
    from routes.admin import admin_bp
    from routes.files import files_bp
    from routes.api import api_bp, _serve_preview
    from routes.search import search_bp

    for bp in (auth_bp, student_bp, teacher_bp, admin_bp, files_bp, api_bp, search_bp):
        app.register_blueprint(bp)

    # ---- Preview endpoint aliases ----------------------------------------
    # Register the SAME view under TWO endpoint names so any template that
    # writes url_for('file_preview', ...) or url_for('api.file_preview', ...)
    # both work.
    app.add_url_rule(
        "/files/<int:fid>/preview",
        endpoint="file_preview",          # <-- the alias used by templates
        view_func=_serve_preview,
        methods=["GET"],
    )


    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return redirect(url_for("dashboard"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        if current_user.role == "teacher":
            return redirect(url_for("teacher.dashboard"))
        return redirect(url_for("student.dashboard"))

    @app.route("/notices")
    @login_required
    def notices_redirect():
        if current_user.role in ("teacher", "admin"):
            return redirect(url_for("teacher.notices"))
        return redirect(url_for("student.notices"))

    @app.route("/assignments")
    @login_required
    def assignments_redirect():
        if current_user.role in ("teacher", "admin"):
            return redirect(url_for("teacher.assignments"))
        return redirect(url_for("student.assignments"))

    @app.route("/timetable")
    @login_required
    def timetable_redirect():
        if current_user.role in ("teacher", "admin"):
            return redirect(url_for("teacher.timetable"))
        return redirect(url_for("student.timetable"))

    @app.route("/requests")
    @login_required
    def requests_redirect():
        if current_user.role in ("teacher", "admin"):
            return redirect(url_for("teacher.requests_"))
        return redirect(url_for("student.requests_"))

    @app.route("/notifications")
    @login_required
    def notifications_redirect():
        return redirect(url_for("student.notifications"))

    @app.route("/profile")
    @login_required
    def profile_redirect():
        return redirect(url_for("student.profile"))

    @app.route("/manifest.json")
    def manifest():
        return send_from_directory("static", "manifest.json",
                                   mimetype="application/manifest+json")

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                               message="You don't have access to this page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404,
                               message="Page not found."), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("error.html", code=413,
                               message="Upload too large. Try a smaller file."), 413

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", code=400,
                               message="Bad request. Your session may have expired."), 400

    @app.cli.command("init-db")
    def init_db():
        try:
            from scripts.seed import seed_all
        except ImportError:
            from seed import seed_all
        db.create_all()
        seed_all()
        print("Database initialized and seeded.")

    return app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            print(">> Empty database - seeding demo data...")
            try:
                from scripts.seed import seed_all
            except ImportError:
                from seed import seed_all
            seed_all()
    print("=" * 64)
    print("  CampusDesk v2.4 is running -> http://localhost:5000")
    print("=" * 64)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
