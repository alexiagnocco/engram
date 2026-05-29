"""Authentication module for myapp."""
import hashlib
import os
import time
from datetime import datetime, timedelta

# Global config
TOKEN_EXPIRY = 3600
MAX_LOGIN_ATTEMPTS = 5
SESSION_STORE = {}


def hash_password(password):
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt + hashed


def verify_password(stored, provided):
    salt = stored[:16]
    stored_hash = stored[16:]
    new_hash = hashlib.pbkdf2_hmac("sha256", provided.encode(), salt, 100000)
    return stored_hash == new_hash


def create_session(user_id, role="user"):
    token = os.urandom(32).hex()
    SESSION_STORE[token] = {
        "user_id": user_id,
        "role": role,
        "created": time.time(),
        "expires": time.time() + TOKEN_EXPIRY,
    }
    return token


def validate_session(token):
    session = SESSION_STORE.get(token)
    if not session:
        return None
    if time.time() > session["expires"]:
        del SESSION_STORE[token]
        return None
    return session


def cleanup_expired():
    now = time.time()
    expired = [t for t, s in SESSION_STORE.items() if now > s["expires"]]
    for t in expired:
        del SESSION_STORE[t]


def login(username, password, user_db):
    user = user_db.get(username)
    if not user:
        return None
    if not verify_password(user["password_hash"], password):
        return None
    return create_session(user["id"], user.get("role", "user"))


def logout(token):
    if token in SESSION_STORE:
        del SESSION_STORE[token]
        return True
    return False
