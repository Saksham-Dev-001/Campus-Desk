"""CampusDesk launcher — initializes DB and starts the server."""
from app import app
from models import db, User

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            print(">> Empty database detected. Seeding demo data...")
            try:
                from scripts.seed import seed_all
            except ImportError:
                from seed import seed_all
            seed_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
