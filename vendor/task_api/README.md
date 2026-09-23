# Task Management API

A Python and Flask API for managing user-owned tasks. Users register, sign in and manage their tasks through JWT-protected endpoints backed by SQLAlchemy and SQLite.

**Status:** authenticated CRUD and a 98-case pytest integration suite are implemented. The suite covers authentication, ownership isolation, task validation, partial updates, date persistence and password boundaries. See [API_SPEC.md](API_SPEC.md) for the current API contract and remaining limitations.

## Features

- Registration and login with bcrypt password hashing and signed JWT access tokens.
- JWT protection on task creation, listing, retrieval, updates and deletion.
- Ownership checks in database queries: users can access only their own tasks.
- Pydantic validation for user and task input, including allowed status and priority values.
- Partial updates that preserve omitted fields and allow optional fields to be cleared.
- Separate routes, schemas, services, models and serialization helpers.
- Database transaction rollback on failed writes and session cleanup in routes.

## Run locally

The current regression suite was verified with Python 3.13.1. Commands below use Bash, including Git Bash on Windows.

```bash
git clone https://github.com/SLutumba/task-management-api.git
cd task-management-api
python -m venv venv
```

Activate the environment in **Git Bash on Windows**:

```bash
source venv/Scripts/activate
```

On **Linux or macOS**:

```bash
source venv/bin/activate
```

Install the dependencies, create a development secret and start the server from the repository root:

```bash
python -m pip install -r requirements.txt
export APP_ENV=dev
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python -m flask --app main run
```

The server listens at `http://127.0.0.1:5000`. `config.py` loads `.env` through python-dotenv; existing shell variables take precedence. You can put `APP_ENV=dev` and a generated `JWT_SECRET_KEY` in your local, untracked `.env` instead. Never commit that file. Changing the secret invalidates tokens signed with the previous value.

`APP_ENV=dev` selects `app/database.db`, and `APP_ENV=test` selects `test.db`. If APP_ENV is absent after loading `.env`, configuration defaults to `dev`. Unsupported values still return an empty database URL and fail engine initialization. Configuration is read on import, so select the environment and provide the JWT secret before importing the application.

For PowerShell, activate with `.\venv\Scripts\Activate.ps1` and set variables with `$env:APP_ENV = "dev"` and `$env:JWT_SECRET_KEY = "your-generated-secret"`.

SQLite tables are created on application import, and local data is stored in `app/database.db`, relative to the working directory. Table creation does not migrate an existing schema. Schema migrations have not been added yet.

Check that the application responds:

```bash
curl -i http://127.0.0.1:5000/tasks/health
```

Expected: `200 OK` with `{"status":"healthy"}`. The health route is public and is not a database connectivity check.

## Try the task workflow

Register a new account:

```bash
curl -i -X POST http://127.0.0.1:5000/users/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo_user","email":"demo@example.com","password":"DemoPassword123!"}'
```

Registration returns `201` and an `access_token`. For an existing account, sign in instead:

```bash
curl -i -X POST http://127.0.0.1:5000/users/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"DemoPassword123!"}'
```

Copy the returned token into a shell variable. Tokens currently expire after 15 minutes; sign in again for a new token.

```bash
export TOKEN='paste-access-token-here'

curl -i -X POST http://127.0.0.1:5000/tasks/create \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Review API docs","description":"Check examples","status":"To-Do","priority":"Medium","due_date":null}'

curl -i http://127.0.0.1:5000/tasks/ \
  -H "Authorization: Bearer $TOKEN"
```

Use the task ID returned by creation in the remaining requests:

```bash
TASK_ID=1 # Replace with the returned id.

curl -i "http://127.0.0.1:5000/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN"

curl -i -X PATCH "http://127.0.0.1:5000/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"status":"Complete","description":null}'

curl -i -X DELETE "http://127.0.0.1:5000/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN"
```

Deletion returns `204` with no body. Accessing a missing task or another user's task returns `404`.

## Endpoint overview

Paths have no `/api` prefix. The table shows the current implementation's success codes.

| Method | Path | Authentication | Success |
|---|---|---|---|
| POST | `/users/register` | Public | `201`, access token |
| POST | `/users/login` | Public | `200`, access token |
| POST | `/tasks/create` | Bearer token | `201`, task object |
| GET | `/tasks/` | Bearer token | `200`, task array |
| GET | `/tasks/{task_id}` | Bearer token | `200`, task object |
| PATCH | `/tasks/{task_id}` | Bearer token | `200`, updated task |
| DELETE | `/tasks/{task_id}` | Bearer token | `204`, empty body |
| GET or POST | `/users/health`, `/tasks/health` | Public | `200`, health object |

Creation returns `201`; retrieval and updates return `200`. Use the trailing slash in `/tasks/`.

## Implementation

| Location | Responsibility |
|---|---|
| `main.py` | Flask application, blueprint registration and JWT configuration |
| `app/api/` | HTTP handling, token identity, validation and application-error responses |
| `app/schemas/` | Pydantic request models and field validation |
| `app/services/` | Task ownership queries, business rules and database writes |
| `app/models/` | SQLAlchemy user/task tables and relationships |
| `app/database.py` | SQLite engine, session factory and initial table creation |
| `config.py` | Loads environment settings and selects the database URL |
| `tests/` | pytest integration coverage and disposable database fixtures |
| `app/utils/` | Password hashing and task serialization helpers |

Each task has one owner through `user_id`; a user can own many tasks. Ownership is taken from the authenticated token, not a request body. Single-task queries filter by both task ID and owner ID, so missing and inaccessible tasks produce the same status code.

For PATCH requests, `model_dump(exclude_unset=True)` distinguishes an omitted field from an explicit `null`. This allows a description or due date to be cleared without overwriting unrelated fields.

Usernames must have at least three characters after stripping whitespace and at most 32 characters in the submitted value; the service stores the stripped value. Task titles require at least three characters after stripping and at most 64 in the submitted value, but preserve surrounding whitespace when stored. Whitespace-only and padded one- or two-character values are rejected.

## Run the tests

From the repository root, with your virtual environment active:

```bash
export JWT_SECRET_KEY='local-test-only-secret-at-least-32-characters'
python -m pytest -v
```

PowerShell equivalent:

```powershell
$env:JWT_SECRET_KEY = 'local-test-only-secret-at-least-32-characters'
python -m pytest -v
```

The test modules set `APP_ENV=test` before application imports. No running Flask server is needed. The authentication tests use the configured JWT secret; the task and boundary suites temporarily use a dedicated test secret.

Fixtures check that the engine points to `test.db`, drop and recreate its tables before each test, and drop them again afterwards. **Treat `test.db` as disposable.** Do not run concurrent suites against this shared file. These fixtures do not modify the development database.

| File | Cases | Coverage |
|---|---:|---|
| `tests/test_auth.py` | 17 | Registration, independent duplicate checks, login and missing fields |
| `tests/test_tasks.py` | 71 | JWT rejection, task CRUD, ownership, validation, nullable fields and UTC date round trips |
| `tests/test_auth_boundaries.py` | 10 | Password character/byte boundaries, response redaction and consistent credential errors |

The suite passed against an isolated copy of the application on 18 September 2026 using Python 3.13.1. Tests assert responses and persisted state, including that rejected operations leave tasks unchanged. They are regression coverage, not an exhaustive security audit or concurrency test.

## Remaining work

- Give unsupported `APP_ENV` values a clear error; the missing-value development default now works.
- Standardize the JSON error envelope across application, JWT and framework errors.
- Decide whether date responses should use ISO 8601 to match request input. Current responses use HTTP date strings at second precision.
- Add CI and database migrations; test concurrency and unexpected database failures separately.

Filtering, pagination, refresh/logout endpoints and deployment are not implemented. These are separate enhancements; the current task workflow does not depend on them.

## License

A license has not yet been selected.
