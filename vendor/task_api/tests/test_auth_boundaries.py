"""Password boundaries and response redaction regression tests."""
import pytest

# Reuse the isolated database fixture and HTTP helpers from the task suite.
from test_tasks import client, check


def register(client, password):
    return client.post('/users/register', json={
        'username': 'boundaryuser', 'email': 'boundary@example.com', 'password': password,
    })


@pytest.mark.parametrize('password', ['x' * 8, 'x' * 64, 'é' * 36])
def test_password_boundaries_allow_registration_and_login(client, password):
    check(register(client, password), 201)
    check(client.post('/users/login', json={
        'email': 'boundary@example.com', 'password': password,
    }), 200)


@pytest.mark.parametrize('password', ['x' * 7, 'x' * 65, 'é' * 37])
@pytest.mark.parametrize('endpoint', ['register', 'login'])
def test_invalid_password_lengths_are_rejected_without_echoing_input(client, password, endpoint):
    if endpoint == 'login':
        check(register(client, 'OriginalPassword123'), 201)
    response = client.post(f'/users/{endpoint}', json={
        'username': 'boundaryuser', 'email': 'boundary@example.com', 'password': password,
    })
    data = check(response, 400)
    assert password not in response.get_data(as_text=True)
    assert 'access_token' not in data


def test_wrong_password_and_unknown_account_have_same_response(client):
    check(register(client, 'OriginalPassword123'), 201)
    known = client.post('/users/login', json={
        'email': 'boundary@example.com', 'password': 'WrongPassword123',
    })
    unknown = client.post('/users/login', json={
        'email': 'unknown@example.com', 'password': 'WrongPassword123',
    })
    assert check(known, 401) == check(unknown, 401)
