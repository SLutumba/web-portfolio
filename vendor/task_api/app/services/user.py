from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.user import RegisterUserRequest, LoginUserRequest
from app.utils.security import hash_password, verify_password
from app.exceptions import DuplicateUserError, InvalidCredentialsError

def register_user(
        db: Session,
        request: RegisterUserRequest
        ) -> User:

    # Sanitise inputs
    email = request.email.strip()
    username = request.username.strip()
    
    # ensure no user with same email/username can be found
    existing_user = (
        db.query(User)
        .filter(
             or_(User.email == email, 
                User.username == username)
        )
        .first()
    )

    if existing_user is not None:
        raise DuplicateUserError(
            "A user with this email/username already exists."
        )

    hashed_password = hash_password(request.password)

    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_password
        )

    db.add(new_user)

    try:
        db.commit()
    except IntegrityError:
         db.rollback()
         raise DuplicateUserError(
            "A user with this email/username already exists."
         )
    except Exception:
        db.rollback()
        raise

    db.refresh(new_user)

    return new_user

def login_user(
        db: Session,
        login_request: LoginUserRequest
    ) -> User:

    email = login_request.email.strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if user is None:
        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    if not verify_password(
        login_request.password, 
        user.password_hash
        ):
            raise InvalidCredentialsError(
                "Invalid email or password."
            )

    return user