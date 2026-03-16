"""Data access layer for faculty records."""

from models import Faculty, db


def get_faculty_for_matching():
    """Return faculty dicts for the matching pipeline.

    Uses enriched research_interests when available, falls back to original.
    Only returns faculty who have at least one source of research interest data.
    """
    all_faculty = Faculty.query.all()

    with_interests = []
    without_interests = []

    for f in all_faculty:
        d = f.to_dict()
        effective_interests = f.research_interests_enriched or f.research_interests
        if effective_interests:
            d["_effective_interests"] = effective_interests
            with_interests.append(d)
        else:
            without_interests.append(d)

    return with_interests, without_interests


def get_all_faculty(department=None, school=None, has_interests=None):
    """Query faculty with optional filters."""
    query = Faculty.query

    if department:
        query = query.filter(Faculty.department == department)
    if school:
        query = query.filter(Faculty.school == school)
    if has_interests is True:
        query = query.filter(
            db.or_(
                Faculty.research_interests.isnot(None),
                Faculty.research_interests_enriched.isnot(None),
            )
        )
    elif has_interests is False:
        query = query.filter(
            Faculty.research_interests.is_(None),
            Faculty.research_interests_enriched.is_(None),
        )

    return [f.to_dict() for f in query.all()]


def get_faculty_by_id(faculty_id):
    """Get a single faculty member by ID."""
    f = Faculty.query.get(faculty_id)
    return f.to_dict() if f else None


def search_faculty(query_text):
    """Search faculty by name or research interests (simple LIKE search)."""
    pattern = f"%{query_text}%"
    results = Faculty.query.filter(
        db.or_(
            Faculty.first_name.ilike(pattern),
            Faculty.last_name.ilike(pattern),
            Faculty.research_interests.ilike(pattern),
            Faculty.research_interests_enriched.ilike(pattern),
        )
    ).all()
    return [f.to_dict() for f in results]


def update_faculty(faculty_id, data):
    """Update a faculty record. Returns the updated dict or None."""
    f = Faculty.query.get(faculty_id)
    if not f:
        return None

    for key, value in data.items():
        if hasattr(f, key) and key not in ("id", "created_at"):
            setattr(f, key, value)

    db.session.commit()
    return f.to_dict()
