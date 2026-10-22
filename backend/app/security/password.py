import logging
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

logger = logging.getLogger("prahari.security.password")

# Standard Argon2id password hasher
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    if not password:
        raise ValueError("Password cannot be empty")
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against stored Argon2id hash.
    Strictly verifies cryptographic hash. No plaintext fallback.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as e:
        logger.warning("Unexpected error during password verification: %s", str(e))
        return False
