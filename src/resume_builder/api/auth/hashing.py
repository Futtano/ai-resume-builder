"""Password hashing with bcrypt."""

import bcrypt


def hash_password(password: str) -> str:
    """Return bcrypt hash of the password as a string."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
