# Shekinah Lutumba · Portfolio

A responsive portfolio featuring my experience, projects, downloadable CV and an interactive Task Management API demo.

Built with HTML, CSS, JavaScript and Flask. Includes light/dark themes and keyboard-accessible navigation.

## Run locally

From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:5173 server:app
```

Open **http://127.0.0.1:5173**.

On macOS/Linux, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

No frontend build step is required. Reload after frontend changes; restart the server after backend changes.

## API demo

The demo uses the Flask Task Management API in `vendor/task_api`, mounted at `/api/tasks`. Requests execute the API’s routes, validation, services and ownership checks.

- Each demo workspace starts with three sample tasks and expires after one hour.
- Supports task creation, retrieval, updates and deletion, with a response inspector.
- Requires no registration or personal information.
- Allows up to 30 tasks per workspace, with request and session rate limits.
- Stores session credentials in browser session storage. Reloading preserves the session; resetting creates a new workspace.
- Expired workspaces become inaccessible immediately and are cleaned up on subsequent API activity.

Runtime data and the generated local signing key are stored in the ignored `data/` directory. The demo is temporary and should not be used for persistent storage.

## Project files

| Path | Purpose |
|---|---|
| `static/index.html` | Portfolio content and links |
| `static/styles.css` | Styling and responsive layouts |
| `static/app.js` | Navigation and demo interactions |
| `static/theme.js` | Theme selection |
| `static/assets/` | Portrait and downloadable CV |
| `server.py` | Flask server and demo sessions |
| `vendor/task_api/` | Task API snapshot |
| `docs/build_cv.py` | PDF CV generation using ReportLab |
| `tests/` | Portfolio integration tests |

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/app.js
```

Tests use an isolated, in-memory SQLite database and cover CRUD, ownership, validation, session expiry, cleanup, limits and static assets.

## Deployment

The included Dockerfile runs Waitress on port **8080** as a non-root user. A Python/container host is required; static-only hosting cannot run the API demo.

- Enable HTTPS.
- Set `JWT_SECRET_KEY` to a strong secret of at least 32 characters through the host’s secret storage.
- Use one application process and instance: SQLite and the rate limiter are configured for a small demo.
- Optionally set `PORTFOLIO_DB_URL` to a SQLite database in a writable mounted directory.
- Enable `TRUST_PROXY=1` only behind exactly one trusted proxy that overwrites forwarding headers and blocks direct access to the application port.

Multiple processes or replicas require shared rate-limit storage and a review of database concurrency.