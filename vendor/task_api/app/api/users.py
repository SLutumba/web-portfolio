from flask import Blueprint, request
from flask_jwt_extended import create_access_token
from pydantic import ValidationError

from app.database import SessionLocal
from app.schemas.user import LoginUserRequest, RegisterUserRequest
from app.services.user import login_user, register_user
from app.exceptions import InvalidCredentialsError, DuplicateUserError, InvalidPasswordError

user_blueprint = Blueprint('users', 'users', url_prefix="/users")

@user_blueprint.route("/health", methods=['GET', 'POST'])
def health_check():
    return {"status": "healthy"}

@user_blueprint.route("/register", methods=["POST"])
def register():

    try:
        payload = request.get_json()
        register_request = RegisterUserRequest.model_validate(payload)
    except ValidationError as exc:
        return {"error": "Invalid request data",
                "details": exc.errors()[0]["msg"]}, 400 # Removed the input from the error message BUT error message seems to vague: (MUST FIX)

    db = SessionLocal()
    try:
        user = register_user(db, register_request)
        user_id = str(user.id)
        access_token = create_access_token(user_id)
    except DuplicateUserError as exc:
        return {"error": str(exc)}, 409
    except InvalidPasswordError as pe:
        return {"error": str(pe)}, 400
    finally:
        db.close()

    return {"access_token": access_token}, 201

@user_blueprint.route("/login", methods=['POST'])
def login():
    
    try:
        payload = request.get_json()
        login_request = LoginUserRequest.model_validate(payload)
    except ValidationError as exc:
        return {"error": "Invalid request data",
                "details": exc.errors()[0]["msg"]}, 400

    db = SessionLocal()
    # used a try, finally block because if errors are encountered,
    # the db.close() may not run, leaving the database session open
    try:
        user = login_user(db, login_request)
        user_id = str(user.id)
        access_token = create_access_token(user_id)

    except InvalidCredentialsError as exc:
        return {"error": str(exc)}, 401
    except InvalidPasswordError as pe:
        return {"error": str(pe)}, 400
    finally:
        db.close()

    return {"access_token": access_token}, 200