"""Role-based authorization and direct-URL access tests (FR-03, NFR-02)."""
from app.models import User, db
from tests.conftest import make_event, login, post


def test_anonymous_user_redirected_from_dashboard_to_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_anonymous_user_redirected_from_manage_page(client):
    assert client.get("/manage/events").status_code == 302


def test_student_forbidden_from_create_event_page(app, client, world):
    login(client, "s1@test.edu")
    assert client.get("/manage/events/new").status_code == 403


def test_student_forbidden_from_admin_dashboard_by_direct_url(app, client, world):
    login(client, "s1@test.edu")
    assert client.get("/admin/dashboard").status_code == 403
    assert client.get("/admin/users").status_code == 403


def test_student_cannot_post_directly_to_organizer_endpoint(app, client, world):
    event_id = make_event(app, world["org1"])
    login(client, "s1@test.edu")
    response = post(client, f"/manage/events/{event_id}/status", {"status": "cancelled"})
    assert response.status_code == 403


def test_organizer_cannot_edit_another_organizers_event(app, client, world):
    event_id = make_event(app, world["org2"])
    login(client, "org1@test.edu")
    assert client.get(f"/manage/events/{event_id}/edit").status_code == 403
    response = post(client, f"/manage/events/{event_id}/status", {"status": "closed"})
    assert response.status_code == 403


def test_organizer_can_edit_own_event(app, client, world):
    event_id = make_event(app, world["org1"], title="Original Title")
    login(client, "org1@test.edu")
    assert client.get(f"/manage/events/{event_id}/edit").status_code == 200


def test_admin_can_manage_any_organizers_event(app, client, world):
    event_id = make_event(app, world["org1"])
    login(client, "admin@test.edu")
    assert client.get(f"/manage/events/{event_id}/edit").status_code == 200
    response = post(client, f"/manage/events/{event_id}/status", {"status": "closed"})
    assert response.status_code == 302


def test_organizer_cannot_change_user_roles(app, client, world):
    login(client, "org1@test.edu")
    response = post(client, f"/admin/users/{world['s1']}/role", {"role": "organizer"})
    assert response.status_code == 403
    with app.app_context():
        assert db.session.get(User, world["s1"]).role == "student"


def test_admin_promotes_student_to_organizer(app, client, world):
    login(client, "admin@test.edu")
    response = post(client, f"/admin/users/{world['s2']}/role", {"role": "organizer"})
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(User, world["s2"]).role == "organizer"


def test_admin_cannot_assign_admin_role_through_ui(app, client, world):
    login(client, "admin@test.edu")
    response = post(client, f"/admin/users/{world['s1']}/role", {"role": "admin"})
    assert response.status_code == 400
    with app.app_context():
        assert db.session.get(User, world["s1"]).role == "student"


def test_admin_cannot_change_own_role(app, client, world):
    login(client, "admin@test.edu")
    post(client, f"/admin/users/{world['admin']}/role", {"role": "student"})
    with app.app_context():
        assert db.session.get(User, world["admin"]).role == "admin"


def test_nonexistent_event_returns_custom_404_page(client, world):
    login(client, "s1@test.edu")
    response = client.get("/events/99999")
    assert response.status_code == 404
    assert b"Page not found" in response.data
