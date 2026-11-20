"""Authentication, registration and session tests (FR-01, FR-02, NFR security)."""
from app.models import User
from tests.conftest import PASSWORD, csrf_token, login, make_user, post


def test_student_registration_creates_student_account(app, client):
    response = post(client, "/register", {
        "full_name": "Ayesha Khan", "email": "ayesha@campus.edu",
        "password": "Strong1pass", "confirm_password": "Strong1pass",
    })
    assert response.status_code == 302
    with app.app_context():
        user = User.query.filter_by(email="ayesha@campus.edu").one()
        assert user.role == "student"
        assert user.password_hash != "Strong1pass"  # stored hashed, never plain


def test_public_registration_ignores_submitted_role(app, client):
    post(client, "/register", {
        "full_name": "Sneaky User", "email": "sneaky@campus.edu", "role": "admin",
        "password": "Strong1pass", "confirm_password": "Strong1pass",
    })
    with app.app_context():
        assert User.query.filter_by(email="sneaky@campus.edu").one().role == "student"


def test_registration_rejects_invalid_email_and_mismatched_passwords(app, client):
    response = post(client, "/register", {
        "full_name": "Bad Email", "email": "not-an-email",
        "password": "Strong1pass", "confirm_password": "Different1",
    })
    assert response.status_code == 200
    assert b"valid email address" in response.data
    assert b"Passwords do not match" in response.data
    with app.app_context():
        assert User.query.filter_by(email="not-an-email").first() is None


def test_password_boundary_seven_characters_rejected_eight_accepted(app, client):
    seven = post(client, "/register", {
        "full_name": "Short Pass", "email": "short@campus.edu",
        "password": "Abcdef1", "confirm_password": "Abcdef1",
    })
    assert b"at least 8 characters" in seven.data
    eight = post(client, "/register", {
        "full_name": "Exact Pass", "email": "exact@campus.edu",
        "password": "Abcdefg1", "confirm_password": "Abcdefg1",
    })
    assert eight.status_code == 302


def test_password_without_digit_is_rejected(client):
    response = post(client, "/register", {
        "full_name": "No Digit", "email": "nodigit@campus.edu",
        "password": "OnlyLetters", "confirm_password": "OnlyLetters",
    })
    assert b"at least one letter and one number" in response.data


def test_duplicate_email_registration_rejected(app, client):
    make_user(app, "taken@campus.edu", "student")
    response = post(client, "/register", {
        "full_name": "Second", "email": "taken@campus.edu",
        "password": "Strong1pass", "confirm_password": "Strong1pass",
    })
    assert b"already exists" in response.data


def test_login_and_logout_round_trip(app, client):
    make_user(app, "login@campus.edu", "student")
    response = login(client, "login@campus.edu")
    assert response.status_code == 302
    assert client.get("/dashboard").status_code == 200

    client.post("/logout", data={"csrf_token": csrf_token(client)})
    assert client.get("/dashboard").status_code == 302  # back to login


def test_wrong_password_is_rejected_with_generic_message(app, client):
    make_user(app, "wrong@campus.edu", "student")
    response = login(client, "wrong@campus.edu", password="Incorrect9")
    assert response.status_code == 200
    assert b"Incorrect email or password" in response.data


def test_post_without_csrf_token_is_rejected(app, client):
    make_user(app, "csrf@campus.edu", "student")
    response = client.post("/login", data={"email": "csrf@campus.edu", "password": PASSWORD})
    assert response.status_code == 400
    assert b"form session expired" in response.data


def test_open_redirect_after_login_is_blocked(app, client):
    make_user(app, "redir@campus.edu", "student")
    response = post(client, "/login?next=https://evil.example",
                    {"email": "redir@campus.edu", "password": PASSWORD, "next": "https://evil.example"})
    assert response.status_code == 302
    assert "evil.example" not in response.headers["Location"]
