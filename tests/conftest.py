"""Shared pytest fixtures. Every test gets its own temporary SQLite database."""
from datetime import timedelta

import pytest

from app import create_app
from app.models import EVENT_OPEN, Event, Registration, User, db, now

PASSWORD = "Test@1234"


@pytest.fixture
def app(tmp_path):
    db_file = tmp_path / "test_campus.db"
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file.as_posix()}",
        "CSRF_ENABLED": True,
    })
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def make_user(app, email, role, name=None, password=PASSWORD):
    with app.app_context():
        user = User(full_name=name or email.split("@")[0].title(), email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def make_event(app, organizer_id, capacity=2, days=7, status=EVENT_OPEN, title="Test Event",
               category="Technology"):
    with app.app_context():
        start = now() + timedelta(days=days)
        event = Event(
            title=title, description="A detailed description for testing purposes.",
            category=category, venue="Hall 1", starts_at=start,
            ends_at=start + timedelta(hours=2), capacity=capacity, status=status,
            organizer_id=organizer_id,
        )
        db.session.add(event)
        db.session.commit()
        return event.id


def csrf_token(client):
    with client.session_transaction() as sess:
        if "csrf_token" not in sess:
            sess["csrf_token"] = "test-token"
        return sess["csrf_token"]


def post(client, url, data=None, **kwargs):
    """POST with a valid CSRF token, as a browser form would send it."""
    payload = dict(data or {})
    payload["csrf_token"] = csrf_token(client)
    return client.post(url, data=payload, **kwargs)


def login(client, email, password=PASSWORD):
    return post(client, "/login", {"email": email, "password": password})


def registration_status(app, user_id, event_id):
    with app.app_context():
        reg = Registration.query.filter(
            Registration.user_id == user_id, Registration.event_id == event_id,
        ).order_by(Registration.id.desc()).first()
        return reg.status if reg else None


def event_snapshot(app, event_id):
    with app.app_context():
        event = db.session.get(Event, event_id)
        return {"status": event.status, "capacity": event.capacity, "title": event.title}


@pytest.fixture
def world(app):
    """Standard cast: one admin, two organizers, three students."""
    return {
        "admin": make_user(app, "admin@test.edu", "admin"),
        "org1": make_user(app, "org1@test.edu", "organizer"),
        "org2": make_user(app, "org2@test.edu", "organizer"),
        "s1": make_user(app, "s1@test.edu", "student"),
        "s2": make_user(app, "s2@test.edu", "student"),
        "s3": make_user(app, "s3@test.edu", "student"),
    }
