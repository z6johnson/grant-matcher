"""Database initialization and seeding for grant-match."""

import json
import logging
import os

from models import Faculty, db

logger = logging.getLogger(__name__)


def init_db(app):
    """Initialize the database with the Flask app."""
    database_url = os.getenv("DATABASE_URL", "")

    # Default to SQLite for local development
    if not database_url:
        db_path = os.path.join(os.path.dirname(__file__), "data", "grant_match.db")
        database_url = f"sqlite:///{db_path}"

    # Neon/Render Postgres URLs use postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        _seed_if_empty()


def _seed_if_empty():
    """Seed the faculty table from faculty.json if the table is empty."""
    if Faculty.query.first() is not None:
        logger.info("Faculty table already populated, skipping seed.")
        return

    json_path = os.path.join(os.path.dirname(__file__), "data", "faculty.json")
    if not os.path.exists(json_path):
        logger.warning("No faculty.json found at %s, skipping seed.", json_path)
        return

    with open(json_path) as f:
        data = json.load(f)

    faculty_list = data.get("faculty", [])
    source_url = data.get("source_url", "")
    school = data.get("school", "")

    count = 0
    for record in faculty_list:
        faculty = Faculty(
            first_name=record["first_name"],
            last_name=record["last_name"],
            degrees=record.get("degrees"),
            title=record.get("title"),
            email=record.get("email"),
            research_interests=record.get("research_interests"),
            school=school,
            source_url=source_url,
        )
        db.session.add(faculty)
        count += 1

    db.session.commit()
    logger.info("Seeded %d faculty records from faculty.json.", count)
