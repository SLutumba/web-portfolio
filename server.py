"""Portfolio and isolated, expiring workspaces using Shekinah's Task API."""
from __future__ import annotations

import os
import secrets
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
os.environ.setdefault("PORTFOLIO_DB_URL", f"sqlite:///{(DATA / 'demo.sqlite3').as_posix()}")
sys.path.insert(0, str(ROOT / "vendor" / "task_api"))

from flask import Flask, jsonify, request, send_from_directory
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity, verify_jwt_in_request
from sqlalchemy import Column, DateTime, ForeignKey, Integer, delete, select
from app.database import SessionLocal, engine
from app.models import Base, Task, User
from app.api.tasks import task_blueprint


class DemoSession(Base):
    __tablename__ = "portfolio_demo_session"
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    expires_at = Column(DateTime, nullable=False, index=True)


Base.metadata.create_all(engine)

app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")
secret = os.environ.get("JWT_SECRET_KEY")
if not secret:
    secret_file = DATA / ".demo-secret"
    try:
        with secret_file.open("x", encoding="utf-8") as handle:
            handle.write(secrets.token_hex(32))
        secret_file.chmod(0o600)
    except FileExistsError:
        pass
    secret = secret_file.read_text(encoding="utf-8").strip()
if len(secret) < 32:
    raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters.")

app.config.update(JWT_SECRET_KEY=secret, JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1), MAX_CONTENT_LENGTH=16_384)
JWTManager(app)
app.register_blueprint(task_blueprint, url_prefix="/api/tasks")

if os.environ.get("TRUST_PROXY") == "1":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

rate_lock = Lock()
session_lock = Lock()
rate_buckets = defaultdict(deque)
last_cleanup = 0.0


def allow_request(key, limit, window):
    now = time.monotonic()
    with rate_lock:
        for stale in list(rate_buckets):
            if not rate_buckets[stale] or rate_buckets[stale][-1] < now - 600:
                del rate_buckets[stale]
        if key not in rate_buckets and len(rate_buckets) >= 4096:
            return False
        bucket = rate_buckets[key]
        while bucket and bucket[0] <= now - window:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def cleanup_expired():
    """Remove expired demo data; never touch non-demo accounts."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as db:
        expired = list(db.scalars(select(DemoSession.user_id).where(DemoSession.expires_at <= now)))
        if expired:
            db.execute(delete(Task).where(Task.user_id.in_(expired)))
            db.execute(delete(DemoSession).where(DemoSession.user_id.in_(expired)))
            db.execute(delete(User).where(User.id.in_(expired)))
            db.commit()


@app.before_request
def protect_demo():
    global last_cleanup
    if not request.path.startswith("/api/"):
        return None
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
            return {"error": "This request must come from the portfolio."}, 403
        if not request.is_json:
            return {"error": "Please send JSON."}, 415
    if not allow_request((request.remote_addr, "requests"), 240, 60):
        return {"error": "A few too many requests. Please try again in a minute."}, 429, {"Retry-After": "60"}
    if time.monotonic() - last_cleanup > 60:
        with session_lock:
            cleanup_expired()
            last_cleanup = time.monotonic()
    if request.path.startswith("/api/tasks"):
        verify_jwt_in_request()
        if not get_jwt().get("portfolio_demo"):
            return {"error": "Start a new demo workspace to continue."}, 401
        try:
            user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            return {"error": "Invalid demo session."}, 401
        with SessionLocal() as db:
            demo = db.get(DemoSession, user_id)
            user = db.get(User, user_id)
            if (not demo or not user or get_jwt().get("demo_name") != user.username
                    or demo.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None)):
                return {"error": "Your demo has expired. Start a fresh workspace."}, 401
            if request.path == "/api/tasks/create" and request.method == "POST":
                if db.query(Task).filter(Task.user_id == user_id).count() >= 30:
                    return {"error": "This demo holds up to 30 tasks. Delete a task to add another."}, 409


@app.after_request
def response_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/demo/session")
def start_demo():
    if not allow_request((request.remote_addr, "sessions"), 12, 600):
        return {"error": "Please wait a few minutes before starting another workspace."}, 429, {"Retry-After": "600"}
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    with session_lock, SessionLocal() as db:
        if db.query(DemoSession).count() >= 2000:
            return {"error": "The demo is busy. Please try again later."}, 503
        suffix = secrets.token_hex(10)
        # Demo identities cannot sign in. Only this endpoint issues their tokens.
        user = User(username=f"demo_{suffix}", email=f"{suffix}@demo.invalid", password_hash="!demo-only")
        db.add(user)
        db.flush()
        db.add(DemoSession(user_id=user.id, expires_at=expires.replace(tzinfo=None)))
        for title, description, status, priority in [
            ("Explore the API demo", "You're in. Try completing this task.", "In Progress", "High"),
            ("Make something your own", "Add a task, edit its details, and watch the API respond.", "To-Do", "Medium"),
            ("Skip the sign-up form", "Your own temporary workspace, ready in one click.", "Complete", "Low"),
        ]:
            db.add(Task(user_id=user.id, title=title, description=description, status=status, priority=priority))
        db.commit()
        token = create_access_token(identity=str(user.id), additional_claims={"portfolio_demo": True, "demo_name": user.username})
    return jsonify(access_token=token, expires_at=expires.isoformat()), 201


@app.errorhandler(413)
def payload_too_large(_):
    return {"error": "That request is too large for the demo."}, 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5173")), debug=False)
