"""Registration, waitlist, cancellation, check-in, CSV and integrity tests (FR-08 to FR-12, BR-01 to BR-12)."""
import csv
import io

import pytest
from sqlalchemy.exc import IntegrityError

from app import services
from app.models import EVENT_CLOSED, Event, Registration, User, db
from app.services import BusinessRuleError
from tests.conftest import (login, make_event, post,
                            registration_status)


def _register(app, student_id, event_id):
    with app.app_context():
        student = db.session.get(User, student_id)
        event = db.session.get(Event, event_id)
        return services.register_student(student, event).status


def _reg_id(app, student_id, event_id):
    with app.app_context():
        return Registration.query.filter_by(user_id=student_id, event_id=event_id) \
            .order_by(Registration.id.desc()).first().id


def test_student_registration_confirmed_when_seats_available(app, client, world):
    event_id = make_event(app, world["org1"], capacity=2)
    login(client, "s1@test.edu")
    response = post(client, f"/events/{event_id}/register")
    assert response.status_code == 302
    assert registration_status(app, world["s1"], event_id) == "confirmed"


def test_duplicate_active_registration_is_rejected(app, client, world):
    event_id = make_event(app, world["org1"], capacity=5)
    login(client, "s1@test.edu")
    post(client, f"/events/{event_id}/register")
    response = post(client, f"/events/{event_id}/register", follow_redirects=True)
    assert b"already have an active registration" in response.data
    with app.app_context():
        count = Registration.query.filter_by(user_id=world["s1"], event_id=event_id).count()
        assert count == 1


def test_database_blocks_duplicate_active_registration(app, world):
    event_id = make_event(app, world["org1"], capacity=5)
    _register(app, world["s1"], event_id)
    with app.app_context():
        db.session.add(Registration(user_id=world["s1"], event_id=event_id, status="confirmed"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_full_event_places_new_student_on_waitlist_in_order(app, client, world):
    event_id = make_event(app, world["org1"], capacity=1)
    assert _register(app, world["s1"], event_id) == "confirmed"
    assert _register(app, world["s2"], event_id) == "waitlisted"
    assert _register(app, world["s3"], event_id) == "waitlisted"
    with app.app_context():
        first = services.waitlist_position(Registration.query.filter_by(user_id=world["s2"]).one())
        second = services.waitlist_position(Registration.query.filter_by(user_id=world["s3"]).one())
        assert (first, second) == (1, 2)


def test_cancelling_confirmed_registration_promotes_earliest_waitlisted(app, client, world):
    event_id = make_event(app, world["org1"], capacity=1)
    _register(app, world["s1"], event_id)
    _register(app, world["s2"], event_id)
    _register(app, world["s3"], event_id)

    login(client, "s1@test.edu")
    post(client, f"/registrations/{_reg_id(app, world['s1'], event_id)}/cancel")

    assert registration_status(app, world["s1"], event_id) == "cancelled"
    assert registration_status(app, world["s2"], event_id) == "confirmed"  # earliest promoted
    assert registration_status(app, world["s3"], event_id) == "waitlisted"  # order preserved


def test_cancelling_waitlisted_registration_does_not_promote_anyone(app, client, world):
    event_id = make_event(app, world["org1"], capacity=1)
    _register(app, world["s1"], event_id)
    _register(app, world["s2"], event_id)
    login(client, "s2@test.edu")
    post(client, f"/registrations/{_reg_id(app, world['s2'], event_id)}/cancel")
    assert registration_status(app, world["s1"], event_id) == "confirmed"
    assert registration_status(app, world["s2"], event_id) == "cancelled"


def test_student_cannot_cancel_another_students_registration(app, client, world):
    event_id = make_event(app, world["org1"], capacity=5)
    _register(app, world["s1"], event_id)
    login(client, "s2@test.edu")
    response = post(client, f"/registrations/{_reg_id(app, world['s1'], event_id)}/cancel")
    assert response.status_code == 403
    assert registration_status(app, world["s1"], event_id) == "confirmed"


def test_registration_rejected_for_closed_event(app, client, world):
    event_id = make_event(app, world["org1"], status=EVENT_CLOSED)
    login(client, "s1@test.edu")
    response = post(client, f"/events/{event_id}/register", follow_redirects=True)
    assert b"not accepting registrations" in response.data
    assert registration_status(app, world["s1"], event_id) is None


def test_capacity_cannot_be_reduced_below_confirmed_registrations(app, client, world):
    event_id = make_event(app, world["org1"], capacity=3)
    _register(app, world["s1"], event_id)
    _register(app, world["s2"], event_id)
    with app.app_context():
        event = db.session.get(Event, event_id)
        data = {"title": event.title, "description": event.description, "category": event.category,
                "venue": event.venue, "starts_at": event.starts_at, "ends_at": event.ends_at,
                "capacity": 1, "status": event.status}
        with pytest.raises(BusinessRuleError):
            services.update_event(event, data)


def test_increasing_capacity_promotes_waitlisted_students(app, client, world):
    event_id = make_event(app, world["org1"], capacity=1)
    _register(app, world["s1"], event_id)
    _register(app, world["s2"], event_id)
    login(client, "org1@test.edu")
    with app.app_context():
        event = db.session.get(Event, event_id)
        data = {"title": event.title, "description": event.description, "category": event.category,
                "venue": event.venue, "starts_at": event.starts_at, "ends_at": event.ends_at,
                "capacity": 2, "status": event.status}
        services.update_event(event, data)
    assert registration_status(app, world["s2"], event_id) == "confirmed"


def test_organizer_cannot_register_for_events(app, client, world):
    event_id = make_event(app, world["org2"])
    login(client, "org1@test.edu")
    assert post(client, f"/events/{event_id}/register").status_code == 403


def test_checkin_confirmed_attendee_succeeds(app, client, world):
    event_id = make_event(app, world["org1"], capacity=5)
    _register(app, world["s1"], event_id)
    login(client, "org1@test.edu")
    response = post(client, f"/manage/registrations/{_reg_id(app, world['s1'], event_id)}/checkin")
    assert response.status_code == 302
    with app.app_context():
        assert Registration.query.filter_by(user_id=world["s1"]).one().checked_in_at is not None


def test_checkin_rejected_for_waitlisted_registration(app, client, world):
    event_id = make_event(app, world["org1"], capacity=1)
    _register(app, world["s1"], event_id)
    _register(app, world["s2"], event_id)
    login(client, "org1@test.edu")
    post(client, f"/manage/registrations/{_reg_id(app, world['s2'], event_id)}/checkin",
         follow_redirects=True)
    with app.app_context():
        assert Registration.query.filter_by(user_id=world["s2"]).one().checked_in_at is None


def test_organizer_cannot_checkin_attendee_of_another_organizers_event(app, client, world):
    event_id = make_event(app, world["org2"], capacity=5)
    _register(app, world["s1"], event_id)
    login(client, "org1@test.edu")
    response = post(client, f"/manage/registrations/{_reg_id(app, world['s1'], event_id)}/checkin")
    assert response.status_code == 403


def test_csv_export_contains_attendees_and_neutralises_formulas(app, client, world):
    event_id = make_event(app, world["org1"], capacity=5)
    _register(app, world["s1"], event_id)
    with app.app_context():
        db.session.get(User, world["s1"]).full_name = "=HYPERLINK(\"x\")"
        db.session.commit()
    login(client, "org1@test.edu")
    response = client.get(f"/manage/events/{event_id}/export.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    rows = list(csv.reader(io.StringIO(response.data.decode())))
    assert rows[0] == ["Full Name", "Email", "Status", "Checked In", "Registered At"]
    assert rows[1][0].startswith("'=HYPERLINK")
    assert rows[1][2] == "confirmed"


def test_student_dashboard_counts_are_accurate(app, client, world):
    confirmed_event = make_event(app, world["org1"], capacity=5, title="Confirmed Event")
    waitlist_event = make_event(app, world["org1"], capacity=1, title="Full Event")
    _register(app, world["s1"], confirmed_event)
    _register(app, world["s2"], waitlist_event)
    _register(app, world["s3"], waitlist_event)
    login(client, "s3@test.edu")
    response = client.get("/dashboard")
    assert response.status_code == 200
    with app.app_context():
        stats = services.student_dashboard(db.session.get(User, world["s3"]))
        assert stats["total"] == 1 and stats["waitlisted"] == 1 and stats["confirmed"] == 0


def test_demo_seed_is_idempotent(app):
    with app.app_context():
        first = services.seed_demo_data()
        second = services.seed_demo_data()
        assert first["users"] == 3 and first["events"] == 6
        assert second == {"users": 0, "events": 0}
        assert User.query.filter_by(email="admin@campus.edu").count() == 1
