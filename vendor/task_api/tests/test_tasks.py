"""API integration coverage. No development database or real JWT secret needed."""
import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import pytest
from flask_jwt_extended import create_access_token

os.environ['APP_ENV'] = 'test'

from main import app
from app.database import engine
from app.models import Base


@pytest.fixture
def client():
    assert engine.url.database == 'test.db', 'Refusing to reset a non-test database'
    previous = {key: app.config[key] for key in ('TESTING', 'JWT_SECRET_KEY')}
    app.config.update(TESTING=True, JWT_SECRET_KEY='qa-test-only-key-not-for-production-123456789')
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        with app.test_client() as test_client:
            yield test_client
    finally:
        Base.metadata.drop_all(engine)
        app.config.update(previous)


def check(response, expected):
    assert response.status_code == expected, response.get_data(as_text=True)
    return response.get_json() if response.is_json else None


@pytest.fixture
def accounts(client):
    def register(name):
        data = check(client.post('/users/register', json={
            'username': name, 'email': f'{name}@example.com', 'password': 'TestingPassword123',
        }), 201)
        assert isinstance(data['access_token'], str) and data['access_token']
        return {'Authorization': f"Bearer {data['access_token']}"}
    return register


@pytest.fixture
def owner(accounts):
    return accounts('owner')


@pytest.fixture
def payload():
    return {'title': 'Review the API', 'status': 'To-Do', 'priority': 'Medium'}


@pytest.fixture
def make_task(client, owner, payload):
    def create(headers=None, **changes):
        return check(client.post('/tasks/create', headers=headers or owner,
                                 json={**payload, **changes}), 201)
    return create


ROUTES = [('POST', '/tasks/create'), ('GET', '/tasks/'), ('GET', '/tasks/1'),
          ('PATCH', '/tasks/1'), ('DELETE', '/tasks/1')]


@pytest.mark.parametrize('method,path', ROUTES)
@pytest.mark.parametrize('token_kind,expected', [('missing', 401), ('malformed', 422),
                                               ('expired', 401), ('wrong-signature', 422)])
def test_every_task_route_rejects_invalid_auth(client, method, path, token_kind, expected):
    headers = {}
    if token_kind == 'malformed':
        token = 'not-a-jwt'
    elif token_kind in ('expired', 'wrong-signature'):
        with app.app_context():
            if token_kind == 'expired':
                token = create_access_token(identity='1', expires_delta=timedelta(seconds=-60))
            else:
                secret = app.config['JWT_SECRET_KEY']
                try:
                    app.config['JWT_SECRET_KEY'] = 'different-test-signing-key-1234567890123456'
                    token = create_access_token(identity='1')
                finally:
                    app.config['JWT_SECRET_KEY'] = secret
    if token_kind != 'missing':
        headers['Authorization'] = f'Bearer {token}'
    check(client.open(path, method=method, headers=headers, json={}), expected)


def test_login_token_can_access_protected_routes(client, owner):
    data = check(client.post('/users/login', json={
        'email': 'owner@example.com', 'password': 'TestingPassword123',
    }), 200)
    assert isinstance(data['access_token'], str) and data['access_token']
    assert check(client.get('/tasks/', headers={
        'Authorization': f"Bearer {data['access_token']}"}), 200) == []


def test_create_persists_expected_task_and_defaults(client, owner, make_task, payload):
    task = make_task()
    assert type(task['id']) is int
    assert task == {**payload, 'id': task['id'], 'description': None, 'due_date': None}
    assert check(client.get(f"/tasks/{task['id']}", headers=owner), 200) == task
    assert check(client.get('/tasks/', headers=owner), 200) == [task]


@pytest.mark.parametrize('status', ['To-Do', 'In Progress', 'Complete'])
@pytest.mark.parametrize('priority', ['Low', 'Medium', 'High'])
def test_all_supported_status_and_priority_values(make_task, status, priority):
    task = make_task(status=status, priority=priority)
    assert (task['status'], task['priority']) == (status, priority)


@pytest.mark.parametrize('field', ['title', 'status', 'priority'])
def test_create_requires_mandatory_fields(client, owner, payload, field):
    del payload[field]
    check(client.post('/tasks/create', headers=owner, json=payload), 400)
    assert check(client.get('/tasks/', headers=owner), 200) == []


INVALID = [('title', ''), ('title', '  '), ('title', '   '), ('title', 'ab'),
           ('title', 'x' * 65), ('title', None), ('description', 'x' * 129),
           ('status', 'invalid'), ('status', None), ('priority', 'invalid'),
           ('priority', None), ('due_date', 'not-a-date')]


@pytest.mark.parametrize('field,value', INVALID)
@pytest.mark.parametrize('operation', ['create', 'patch'])
def test_invalid_task_fields_do_not_change_state(client, owner, payload, make_task,
                                                field, value, operation):
    if operation == 'create':
        check(client.post('/tasks/create', headers=owner, json={**payload, field: value}), 400)
        assert check(client.get('/tasks/', headers=owner), 200) == []
    else:
        task = make_task()
        path = f"/tasks/{task['id']}"
        check(client.patch(path, headers=owner, json={field: value}), 400)
        assert check(client.get(path, headers=owner), 200) == task


def test_maximum_lengths_are_accepted(make_task):
    task = make_task(title='x' * 64, description='y' * 128)
    assert task['title'] == 'x' * 64
    assert task['description'] == 'y' * 128


def test_patch_preserves_omitted_fields_and_persists_changes(client, owner, make_task):
    task = make_task(description='Keep this description')
    path = f"/tasks/{task['id']}"
    changes = {'title': 'Updated task', 'status': 'Complete', 'priority': 'High'}
    expected = {**task, **changes}
    assert check(client.patch(path, headers=owner, json=changes), 200) == expected
    assert check(client.get(path, headers=owner), 200) == expected
    assert check(client.patch(path, headers=owner, json={}), 200) == expected


def test_patch_can_clear_nullable_fields(client, owner, make_task):
    future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    task = make_task(description='Clear me', due_date=future)
    path = f"/tasks/{task['id']}"
    updated = check(client.patch(path, headers=owner,
                                json={'description': None, 'due_date': None}), 200)
    assert updated == {**task, 'description': None, 'due_date': None}
    assert check(client.get(path, headers=owner), 200) == updated


@pytest.mark.parametrize('operation', ['create', 'patch'])
@pytest.mark.parametrize('kind', ['past', 'naive'])
def test_due_date_rejects_past_or_timezone_missing(client, owner, payload, make_task,
                                                 operation, kind):
    date = datetime.now(timezone.utc) + timedelta(days=-2 if kind == 'past' else 2)
    if kind == 'naive':
        date = date.replace(tzinfo=None)
    if operation == 'create':
        check(client.post('/tasks/create', headers=owner,
                          json={**payload, 'due_date': date.isoformat()}), 400)
        assert check(client.get('/tasks/', headers=owner), 200) == []
    else:
        task = make_task()
        path = f"/tasks/{task['id']}"
        check(client.patch(path, headers=owner, json={'due_date': date.isoformat()}), 400)
        assert check(client.get(path, headers=owner), 200) == task


def test_due_date_preserves_instant_through_create_read_and_patch(client, owner, make_task):
    # The current API emits HTTP dates, which have second precision.
    date = (datetime.now(timezone(timedelta(hours=2))) + timedelta(days=7)).replace(microsecond=0)
    task = make_task(due_date=date.isoformat())
    path = f"/tasks/{task['id']}"
    assert parsedate_to_datetime(task['due_date']) == date
    assert parsedate_to_datetime(check(client.get(path, headers=owner), 200)['due_date']) == date
    changed = date + timedelta(days=1)
    updated = check(client.patch(path, headers=owner, json={'due_date': changed.isoformat()}), 200)
    assert parsedate_to_datetime(updated['due_date']) == changed
    preserved = check(client.patch(path, headers=owner, json={'title': 'Date unchanged'}), 200)
    assert parsedate_to_datetime(preserved['due_date']) == changed


def test_delete_removes_only_target_task(client, owner, make_task):
    target, survivor = make_task(), make_task(title='Keep this task')
    path = f"/tasks/{target['id']}"
    response = client.delete(path, headers=owner)
    check(response, 204)
    assert response.data == b''
    check(client.get(path, headers=owner), 404)
    check(client.delete(path, headers=owner), 404)
    assert check(client.get('/tasks/', headers=owner), 200) == [survivor]


@pytest.mark.parametrize('method', ['GET', 'PATCH', 'DELETE'])
def test_other_users_tasks_are_hidden_and_unchanged(client, owner, accounts, make_task, method):
    task = make_task()
    other = accounts('otheruser')
    own_task = make_task(headers=other, title='Other users task')
    assert check(client.get('/tasks/', headers=other), 200) == [own_task]
    assert check(client.get('/tasks/', headers=owner), 200) == [task]
    body = {'title': 'Unauthorized change'} if method == 'PATCH' else {}
    hidden = client.open(f"/tasks/{task['id']}", method=method, headers=other, json=body)
    missing = client.open('/tasks/999999', method=method, headers=other, json=body)
    assert check(hidden, 404) == check(missing, 404)
    assert check(client.get(f"/tasks/{task['id']}", headers=owner), 200) == task


def test_request_body_cannot_assign_or_transfer_ownership(client, owner, accounts, make_task):
    other = accounts('otheruser')
    # Fresh database: owner registers first, other user second.
    task = make_task(user_id=2)
    path = f"/tasks/{task['id']}"
    check(client.patch(path, headers=owner, json={'user_id': 2}), 200)
    assert check(client.get(path, headers=owner), 200) == task
    check(client.get(path, headers=other), 404)
    assert check(client.get('/tasks/', headers=other), 200) == []
