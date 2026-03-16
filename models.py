"""SQLAlchemy models for grant-match application."""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Faculty(db.Model):
    __tablename__ = "faculty"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.Text, nullable=False)
    last_name = db.Column(db.Text, nullable=False)
    degrees = db.Column(db.JSON)  # ["MD", "PhD", "MPH"]
    title = db.Column(db.Text)
    email = db.Column(db.Text)
    department = db.Column(db.Text)
    school = db.Column(
        db.Text,
        default="Herbert Wertheim School of Public Health and Human Longevity Science",
    )
    research_interests = db.Column(db.Text)  # original from directory — never overwritten
    research_interests_enriched = db.Column(db.Text)  # LLM-normalized after enrichment
    expertise_keywords = db.Column(db.JSON)  # ["epidemiology", "HIV", ...]
    profile_url = db.Column(db.Text)
    orcid = db.Column(db.Text)
    google_scholar_id = db.Column(db.Text)
    h_index = db.Column(db.Integer)
    recent_publications = db.Column(db.JSON)  # [{title, year, journal}, ...]
    funded_grants = db.Column(db.JSON)  # [{title, agency, amount, year}, ...]
    source_url = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    enrichment_logs = db.relationship("EnrichmentLog", backref="faculty", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("first_name", "last_name", "email", name="uq_faculty_identity"),
    )

    def to_dict(self):
        """Convert to dict matching the format grant_matcher expects."""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "degrees": self.degrees or [],
            "title": self.title or "",
            "email": self.email,
            "research_interests": self.research_interests,
            "research_interests_enriched": self.research_interests_enriched,
            "expertise_keywords": self.expertise_keywords or [],
            "h_index": self.h_index,
            "recent_publications": self.recent_publications or [],
            "funded_grants": self.funded_grants or [],
            "profile_url": self.profile_url,
            "orcid": self.orcid,
        }


class EnrichmentLog(db.Model):
    __tablename__ = "enrichment_log"

    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False)
    source_name = db.Column(db.Text, nullable=False)  # 'ucsd_profile', 'nih_reporter', etc.
    source_url = db.Column(db.Text)
    field_updated = db.Column(db.Text, nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    confidence = db.Column(db.Float)  # 0.0-1.0
    method = db.Column(db.Text)  # 'api', 'scrape', 'llm_extraction'
    raw_response = db.Column(db.Text)
    retrieved_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class MatchAudit(db.Model):
    __tablename__ = "match_audit"

    id = db.Column(db.Integer, primary_key=True)
    run_date = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    grant_filename = db.Column(db.Text)
    grant_title = db.Column(db.Text)
    funding_agency = db.Column(db.Text)
    grant_requirements = db.Column(db.JSON)
    results = db.Column(db.JSON)
    faculty_count = db.Column(db.Integer)
    model_used = db.Column(db.Text)
    processing_seconds = db.Column(db.Float)
