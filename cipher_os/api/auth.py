"""Authentication — username/password login with JWT sessions."""

import secrets
import hashlib
import json
import time
from pathlib import Path
from typing import Optional

import jwt

from ..core.config import get_cipher_home


AUTH_FILE = "credentials.json"
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY = 86400 * 7  # 7 days


def _get_auth_path() -> Path:
    return get_cipher_home() / AUTH_FILE


def _get_jwt_secret() -> str:
    """Get or generate a persistent JWT signing secret."""
    home = get_cipher_home()
    secret_path = home / ".jwt_secret"
    if secret_path.exists():
        return secret_path.read_text().strip()
    secret = secrets.token_hex(32)
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    secret_path.write_text(secret)
    secret_path.chmod(0o600)
    return secret


def _hash_password(password: str, salt: str) -> str:
    """Hash password with salt using SHA-256."""
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def is_setup() -> bool:
    """Check if credentials have been configured."""
    return _get_auth_path().exists()


def setup_credentials(username: str, password: str) -> bool:
    """Set up initial credentials (first run only)."""
    if is_setup():
        raise ValueError("Credentials already configured. Use change_password to update.")

    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)

    auth_data = {
        "username": username,
        "password_hash": password_hash,
        "salt": salt,
        "created_at": time.time(),
    }

    path = _get_auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(auth_data))
    path.chmod(0o600)
    return True


def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password against stored credentials."""
    path = _get_auth_path()
    if not path.exists():
        return False

    auth_data = json.loads(path.read_text())

    if username != auth_data["username"]:
        return False

    password_hash = _hash_password(password, auth_data["salt"])
    return secrets.compare_digest(password_hash, auth_data["password_hash"])


def change_password(current_password: str, new_password: str) -> bool:
    """Change password (requires current password)."""
    path = _get_auth_path()
    if not path.exists():
        raise ValueError("No credentials configured.")

    auth_data = json.loads(path.read_text())
    current_hash = _hash_password(current_password, auth_data["salt"])

    if not secrets.compare_digest(current_hash, auth_data["password_hash"]):
        raise ValueError("Current password is incorrect.")

    new_salt = secrets.token_hex(16)
    new_hash = _hash_password(new_password, new_salt)

    auth_data["password_hash"] = new_hash
    auth_data["salt"] = new_salt

    path.write_text(json.dumps(auth_data))
    return True


def create_token(username: str) -> str:
    """Create a JWT access token."""
    secret = _get_jwt_secret()
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token. Returns username if valid, None if not."""
    secret = _get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
