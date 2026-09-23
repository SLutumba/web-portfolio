import os

import pytest

# Must happen before application imports.
os.environ["APP_ENV"] = "test"

from main import app
from app.models import Base
from app.database import engine


@pytest.fixture
def client():
    app.config["TESTING"] = True

    # Refuse to drop tables unless we're using the expected test DB.
    assert engine.url.database == "test.db", (
        f"Expected test.db, got {engine.url.database!r}"
    )

    # Clear leftovers from an interrupted previous run.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    try:
        with app.test_client() as client:
            yield client
    finally:
        Base.metadata.drop_all(engine)


@pytest.fixture
def user_data():
    return {
        "username": "thebest1",
        "email": "thebest1@gmail.com",
        "password": "thebestfr1",
    }


def assert_status(response, expected):
    assert response.status_code == expected, (
        f"Expected {expected}, got {response.status_code}. "
        f"Response: {response.get_data(as_text=True)}"
    )


@pytest.fixture
def registered_user(client, user_data):
    response = client.post("/users/register", json=user_data)
    assert_status(response, 201)
    return user_data


def test_successful_registration(client, user_data):
    response = client.post("/users/register", json=user_data)

    assert_status(response, 201)


@pytest.mark.parametrize(
    "changes",
    [
        {},  # Same username and email.
        {"email": "another@example.com"},  # Same username only.
        {"username": "anotheruser"},  # Same email only.
    ],
    ids=["both-duplicate", "username-duplicate", "email-duplicate"],
)
def test_duplicate_registration(client, registered_user, changes):
    payload = {**registered_user, **changes}

    response = client.post("/users/register", json=payload)

    assert_status(response, 409)


def test_two_different_users_can_register(client, registered_user):
    response = client.post(
        "/users/register",
        json={
            "username": "anotheruser",
            "email": "another@example.com",
            "password": "anotherpass123",
        },
    )

    assert_status(response, 201)


@pytest.mark.parametrize("field", ["username", "email", "password"])
def test_registration_rejects_missing_fields(client, user_data, field):
    payload = user_data.copy()
    del payload[field]

    response = client.post("/users/register", json=payload)

    assert_status(response, 400)


def test_registration_rejects_invalid_email(client, user_data):
    payload = {**user_data, "email": "not-an-email"}

    response = client.post("/users/register", json=payload)

    assert_status(response, 400)


def test_registration_rejects_empty_body(client):
    response = client.post("/users/register", json={})

    assert_status(response, 400)


def test_successful_login(client, registered_user):
    response = client.post(
        "/users/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert_status(response, 200)


def test_login_rejects_wrong_password(client, registered_user):
    response = client.post(
        "/users/login",
        json={
            "email": registered_user["email"],
            "password": "wrongpassword123",
        },
    )

    assert_status(response, 401)


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/users/login",
        json={
            "email": "unknown@example.com",
            "password": "thebestfr1",
        },
    )

    assert_status(response, 401)


@pytest.mark.parametrize("field", ["email", "password"])
def test_login_rejects_missing_fields(client, user_data, field):
    payload = {
        "email": user_data["email"],
        "password": user_data["password"],
    }
    del payload[field]

    response = client.post("/users/login", json=payload)

    assert_status(response, 400)


def test_login_rejects_empty_body(client):
    response = client.post("/users/login", json={})

    assert_status(response, 400)


def test_rejected_duplicate_does_not_break_original_login(
    client, registered_user
):
    duplicate_response = client.post(
        "/users/register",
        json={
            **registered_user,
            "password": "differentpassword123",
        },
    )
    assert_status(duplicate_response, 409)

    login_response = client.post(
        "/users/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert_status(login_response, 200)