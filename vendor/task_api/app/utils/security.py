import bcrypt

from app.exceptions import InvalidPasswordError

def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise InvalidPasswordError(
            "Your password is too long. Passwords should be under 65 characters and 72 bytes long"
        )
    hashed = bcrypt.hashpw(
        password.encode("utf-8"), 
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    if len(password.encode("utf-8")) > 72:
        raise InvalidPasswordError(
            "Your password is too long. Passwords should be under 65 characters and 72 bytes long"
        )
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )