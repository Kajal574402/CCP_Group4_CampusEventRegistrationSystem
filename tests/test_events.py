"""Event creation, validation, search and filtering tests (FR-04 to FR-07)."""
from datetime import timedelta

from app.models import Event, db, now
from app.validators import validate_event
from tests.conftest import login, make_event, post


def _event_form(days=10, start="10:00", end="12:00", capacity="50", **overrides):
    future = (now() + timedelta(days=days)).strftime("%Y-%m-%d")
    form = {
        "title": "Robotics Workshop", "description": "Hands-on robotics for beginners.",
        "category": "Workshop", "venue": "Lab 4", "event_date": future,
        "start_time": start, "end_time": end, "capacity": capacity, "status": "open",
    }
    form.update(overrides)
    return form


def test_organizer_creates_valid_event(app, client, world):
    login(client, "org1@test.edu")
    response = post(client, "/manage/events/new", _event_form())
    assert response.status_code == 302
    with app.app_context():
        event = Event.query.filter_by(title="Robotics Workshop").one()
        assert event.organizer_id == world["org1"]
        assert event.capacity == 50


def test_event_end_before_start_is_rejected(app, client, world):
    login(client, "org1@test.edu")
    response = post(client, "/manage/events/new", _event_form(start="14:00", end="13:00"))
    assert response.status_code == 200
    assert b"End time must be after the start time" in response.data


def test_event_in_the_past_is_rejected_on_creation(app, client, world):
    login(client, "org1@test.edu")
    response = post(client, "/manage/events/new", _event_form(days=-3))
    assert b"must start in the future" in response.data


def test_capacity_boundaries_zero_rejected_one_accepted(app):
    data, errors = validate_event(_event_form(capacity="0"), require_future=True)
    assert "capacity" in errors
    data, errors = validate_event(_event_form(capacity="1"), require_future=True)
    assert "capacity" not in errors
    _, errors = validate_event(_event_form(capacity="5001"), require_future=True)
    assert "capacity" in errors


def test_event_title_too_short_rejected(app):
    _, errors = validate_event(_event_form(title="ab"), require_future=True)
    assert "title" in errors


def test_student_cannot_create_event(app, client, world):
    login(client, "s1@test.edu")
    response = post(client, "/manage/events/new", _event_form())
    assert response.status_code == 403


def test_organizer_edits_own_event_and_changes_title(app, client, world):
    event_id = make_event(app, world["org1"], title="Old Name")
    login(client, "org1@test.edu")
    response = post(client, f"/manage/events/{event_id}/edit", _event_form(title="New Name"))
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Event, event_id).title == "New Name"


def test_search_matches_event_name_case_insensitively(app, client, world):
    make_event(app, world["org1"], title="Campus Hackathon")
    make_event(app, world["org1"], title="Cultural Night", category="Cultural")
    response = client.get("/events?q=hackathon")
    assert b"Campus Hackathon" in response.data
    assert b"Cultural Night" not in response.data


def test_category_filter_limits_results(app, client, world):
    make_event(app, world["org1"], title="Tech Event Alpha", category="Technology")
    make_event(app, world["org1"], title="Sports Event Beta", category="Sports")
    response = client.get("/events?category=Sports")
    assert b"Sports Event Beta" in response.data
    assert b"Tech Event Alpha" not in response.data


def test_closed_and_past_events_are_hidden_from_browse(app, client, world):
    make_event(app, world["org1"], title="Closed One", status="closed")
    make_event(app, world["org1"], title="Past One", days=-5)
    response = client.get("/events")
    assert b"Closed One" not in response.data
    assert b"Past One" not in response.data
