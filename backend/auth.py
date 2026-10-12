"""Account creation, login, and sessions for Campus Customs.

Passwords are stored as PBKDF2-SHA256 hashes with a random per-user salt; the plain password is
never saved or logged. After logging in, the browser holds a random session token in an HttpOnly
cookie, and the database stores only a SHA-256 hash of that token (in the `sessions` table).
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 600_000  # OWASP's current recommendation for PBKDF2-SHA256
# The accounts that came with the database use 'pbkdf2_sha256$salt$hash' with this fixed count.
LEGACY_ITERATIONS = 120_000
SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter(prefix="/api/auth")


# ---------- Database ----------

def connect_rw() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_sessions_table() -> None:
    """Create the sessions table on startup if it doesn't exist yet."""
    with closing(connect_rw()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")


# ---------- Passwords ----------

def hash_password(password: str) -> str:
    """Return 'pbkdf2_sha256$<iterations>$<salt>$<hash>' (hex-encoded salt and hash)."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), HASH_ITERATIONS)
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == HASH_ALGORITHM and parts[1].isdigit():
        # Accounts created here: 'pbkdf2_sha256$<iterations>$<salt>$<hash>'
        _, iterations, salt, expected = parts
    elif len(parts) == 3 and parts[0] == HASH_ALGORITHM:
        # Accounts that came with the database: 'pbkdf2_sha256$<salt>$<hash>'
        _, salt, expected = parts
        iterations = LEGACY_ITERATIONS
    else:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
    return hmac.compare_digest(digest.hex(), expected)


# Used when an email isn't registered, so a login attempt takes the same time either way
# and doesn't reveal which emails have accounts.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ---------- Login rate limiting (in memory, per email) ----------

_failed_logins: dict[str, list[float]] = {}


def _recent_failures(email: str) -> list[float]:
    cutoff = time.time() - LOCKOUT_SECONDS
    attempts = [t for t in _failed_logins.get(email, []) if t > cutoff]
    _failed_logins[email] = attempts
    return attempts


# ---------- Sessions ----------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(conn: sqlite3.Connection, response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_token_hash(token), user_id, expires.strftime("%Y-%m-%d %H:%M:%S")),
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,  # page scripts can't read the token
        samesite="lax",  # not sent on cross-site form posts
        secure=False,  # local development runs on plain http; set True behind https
        path="/",
    )


def user_for_token(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    return conn.execute(
        """
        SELECT u.id, u.first_name, u.last_name, u.name, u.email, u.created_at
        FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND s.expires_at > datetime('now')
        """,
        (_token_hash(token),),
    ).fetchone()


def public_user(row: sqlite3.Row) -> dict:
    """The account fields that are safe to send to the browser (never the password hash)."""
    first, last = row["first_name"], row["last_name"]
    if not first:
        first, _, last = row["name"].partition(" ")
    return {
        "id": row["id"],
        "first_name": first,
        "last_name": last or "",
        "email": row["email"],
        "created_at": row["created_at"],
    }


# ---------- Request bodies ----------

class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("is required")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("is not a valid email address")
        return v


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


# ---------- Routes ----------

@router.post("/register", status_code=201)
def register(body: RegisterRequest, response: Response) -> dict:
    password_hash = hash_password(body.password)
    with closing(connect_rw()) as conn, conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (name, first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?, ?)",
                (f"{body.first_name} {body.last_name}", body.first_name, body.last_name, body.email, password_hash),
            )
        except sqlite3.IntegrityError:  # users.email is UNIQUE
            raise HTTPException(status_code=409, detail="An account with that email already exists.")
        start_session(conn, response, cur.lastrowid)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return public_user(row)


@router.post("/login")
def login(body: LoginRequest, response: Response) -> dict:
    if len(_recent_failures(body.email)) >= MAX_FAILED_LOGINS:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")

    with closing(connect_rw()) as conn, conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (body.email,)).fetchone()
        ok = verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH)
        if not row or not ok:
            _failed_logins.setdefault(body.email, []).append(time.time())
            # Same message whether the email or the password was wrong.
            raise HTTPException(status_code=401, detail="Incorrect email or password.")
        _failed_logins.pop(body.email, None)
        start_session(conn, response, row["id"])
    return public_user(row)


@router.post("/logout", status_code=204)
def logout(response: Response, cc_session: str | None = Cookie(default=None)) -> None:
    if cc_session:
        with closing(connect_rw()) as conn, conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(cc_session),))
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me")
def me(cc_session: str | None = Cookie(default=None)) -> dict:
    with closing(connect_rw()) as conn:
        row = user_for_token(conn, cc_session)
    if row is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return public_user(row)
