# Shekinah Lutumba · Web portfolio

A responsive, single-page portfolio with a light/dark theme, personal introduction, professional experience, downloadable CV, and an instant-access Task Management API demo.

## Run locally

From this directory, in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:5173 server:app
```

Open **http://127.0.0.1:5173**. On macOS/Linux, replace `.venv\Scripts\python.exe` with `.venv/bin/python`.

There is no frontend build step. After editing HTML, CSS or JavaScript, reload the browser. Restart the Python server after backend changes. `python server.py` also provides a local development preview if the dependencies are already available.

## What is included

- Baby-blue accents, translucent navigation and selected glass panels.
- A theme switch that starts from the device preference and remembers an explicit choice.
- Responsive mobile navigation, keyboard focus styles, semantic sections, a skip link and reduced-motion support.
- Introduction, collaboration example, project details, work/education timeline, creator interests and verified contact links.
- A one-page PDF CV based on the background confirmed in the conversation.
- Real create/read/update/delete calls against the user's Flask Task API, with a visible response inspector.
- No analytics, contact-form service, third-party scripts or font dependencies.

## Demo architecture

`server.py` serves the static portfolio and imports the actual Flask task blueprint from `vendor/task_api`. The vendor snapshot comes from the adjacent Task Management API repository at commit `1c07260a1edc1982d623f470782621f6f4a258f4`.

The original project was not changed. The only change inside the vendored application is the `PORTFOLIO_DB_URL` override in `config.py`. Its route, schema, service and ownership logic are reused, not simulated in the browser. The portfolio mounts its routes under `/api/tasks` instead of `/tasks`.

The portfolio wrapper adds:

1. `POST /api/demo/session`: creates a synthetic, non-login user, three sample tasks and a signed one-hour token. No personal information is collected.
2. An expiring session record. The random demo username is also bound into the token, preventing a deleted/reused SQLite user ID from reviving an older session.
3. Server-side expiry checks and cleanup of expired demo users and their tasks on subsequent API activity (at most once a minute). Expired data can remain on disk while the site is idle but is inaccessible through the API.
4. A 30-task limit, per-process request/session rate limits, a 2,000-workspace cap, same-origin checks, request size limits and response security headers.
5. Session credentials held in browser session storage; they are never placed in URLs or the response inspector. The ordinary account registration/login routes are not exposed by the portfolio.

Filtering is performed in the interface. The public demo is a temporary playground, not a persistent task storage service. It doesn't claim to demonstrate account registration or sign-in. Browser sessions survive reloads until expiry. Reset starts a new workspace; the old one expires normally. Independently opened tabs get separate sessions; browser-duplicated tabs may copy session storage.

Runtime files are kept in `data/`, which is ignored. A local signing key is generated on first use. For a hosted environment, set a strong `JWT_SECRET_KEY` of at least 32 characters using the host's secret storage. Never commit it.

## Files to edit

| File | Purpose |
| --- | --- |
| `static/index.html` | All portfolio copy, sections, contact links and project content |
| `static/styles.css` | Colour tokens, layouts, glass treatments and breakpoints |
| `static/app.js` | Navigation, theme controls and demo interactions |
| `static/theme.js` | Theme selection before the first paint |
| `static/assets/portrait.jpg` | Current public GitHub photo, used as a preview portrait |
| `static/assets/Shekinah-Lutumba-CV.pdf` | Downloadable CV |
| `docs/build_cv.py` | CV source; run with Python and `reportlab` to regenerate |
| `server.py` | Portfolio server and demo-session integration |

To add the Weather App or coding-practice tracker, add another project article in the selected-work section once the project is ready. No empty project cards or pretend demo links are displayed.

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/app.js
```

The portfolio tests use an isolated in-memory SQLite database and cover CRUD, ownership isolation, rejected updates, expiration, cleanup, reused-ID protection, limits, and static assets. They do not touch the running demo or original project database.

To run the original API regression suite, use a separate process from `vendor/task_api`, unset `PORTFOLIO_DB_URL`, set a test-only `JWT_SECRET_KEY`, and run `python -m pytest -q`. Those tests use the vendored `test.db`; don't run multiple suites against that same file at once.

## Hosting

A `Dockerfile` is included for a Python/container host. It runs Waitress on port 8080 as a non-root user. The site needs a Python server; a static-only host will not run the API demo.

Use HTTPS at the host, set `JWT_SECRET_KEY`, and keep one application process/instance for this SQLite demo and its in-memory rate limiter. `PORTFOLIO_DB_URL` can point to a SQLite database in a writable mounted directory. Use `TRUST_PROXY=1` only when deployed behind exactly one trusted proxy that overwrites forwarding headers and prevents direct client access to the application port. Leave it unset locally.

For multiple processes/replicas, first replace the per-process rate limiter with shared storage and review database locking, cleanup and concurrency. The current deployment design is deliberately a small portfolio demo.

No hosting account, paid service, domain, public deployment or remote repository was created in this build.

## Content notes before a public launch

- The current photo is the user's public GitHub avatar. A face-visible portrait is recommended for the final version.
- The downloadable CV is newly drafted from confirmed background and public professional details; review its phrasing before using it in applications.
- The creator section links to the confirmed Instagram account. A specific educational video has not yet been selected, so no fabricated clip, transcript or embed is included.
- The Weather App and coding-practice tracker are future additions; only the completed Task API is featured at launch.
- Education is marked in progress. Dart and Flutter training are complete; Shekinah has officially started work in the Mobile Apps team.
