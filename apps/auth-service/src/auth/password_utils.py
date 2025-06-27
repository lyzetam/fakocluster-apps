import os
import hashlib
import binascii
import hmac

DEFAULT_ITERATIONS = 100_000


def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"{iterations}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        iter_str, salt_hex, hash_hex = hashed.split("$")
        iterations = int(iter_str)
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


