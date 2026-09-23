from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError
from app.database import SessionLocal
from app.exceptions import InvalidDateTimeError, TaskNotFoundError
from app.schemas.task import CreateTaskRequest, UpdateTaskRequest
from app.services.task import get_tasks, create_task, get_task, update_task, delete_task
from app.utils.helper_functions import task_serialiser, tasks_serialiser

task_blueprint = Blueprint('tasks', 'tasks', url_prefix="/tasks")

@task_blueprint.route("/health", methods=['GET', 'POST'])
def health_check():
    return {"status": "healthy"}

@task_blueprint.route("/create", methods=['POST'])
@jwt_required()
def create_user_task():
    current_user_id = int(get_jwt_identity())

    try:
        payload = request.get_json()
        create_request = CreateTaskRequest.model_validate(payload)
    except ValidationError as exc:
        return {"error": "Invalid request data", 
                "details": exc.errors()[0]["msg"]}, 400

    db = SessionLocal()
    try:
        task = create_task(db=db, 
                        request=create_request, 
                        user_id=current_user_id)
    except InvalidDateTimeError as e:
        return {"error": str(e)}, 400
    except Exception:
            return {"error": "Internal Server Error"}, 500

    finally:
        db.close()

    return jsonify(task_serialiser(task)), 201

@task_blueprint.route("/", methods=['GET'])
@jwt_required()
def get_user_tasks():

    current_user_id = int(get_jwt_identity())

    db = SessionLocal()
    try:
        tasks = get_tasks(db, user_id=current_user_id)
    except Exception:
        return {"error": "Internal Server Error"}, 500
    finally:
        db.close()
    
    return jsonify(tasks_serialiser(tasks)), 200

@task_blueprint.route("/<int:task_id>", methods=['GET'])
@jwt_required()
def get_user_task(task_id: int):
    current_user_id = int(get_jwt_identity())

    db = SessionLocal()
    try:
        task = get_task(db=db, user_id=current_user_id, task_id=task_id)
    except TaskNotFoundError as exc:
        return {"error": str(exc)}, 404
    except Exception:
        return {"error": "Internal Server Error"}, 500
    finally:
        db.close()

    return jsonify(task_serialiser(task=task)), 200

@task_blueprint.route("/<int:task_id>", methods=["PATCH"])
@jwt_required()
def update_user_task(task_id: int):
    current_user_id = int(get_jwt_identity())

    try:
        payload = request.get_json()
        update_request = UpdateTaskRequest.model_validate(payload)

    except ValidationError as exc:
            return {"error": "Invalid request data", 
                    "details": exc.errors()[0]["msg"]}, 400

    db = SessionLocal()
    try:
        task = update_task(
            db=db, 
            request=update_request,
            task_id=task_id,
            user_id=current_user_id
            )
    except TaskNotFoundError as exc:
        return {"error": str(exc)}, 404    
    except InvalidDateTimeError as e:
        return {"error": str(e)}, 400
    
    except Exception:
            return {"error": "Internal Server Error"}, 500
    
    finally:
        db.close()
    
    return jsonify(task_serialiser(task))

@task_blueprint.route("/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_user_task(task_id: int):
    current_user_id = int(get_jwt_identity())

    db = SessionLocal()
    try:
        delete_task(db=db, task_id=task_id, user_id=current_user_id)
    except TaskNotFoundError as exc:
        return {"error": str(exc)}, 404
    except Exception as e:
        print(f"Error encountered in delete route: {e}")
        return {"error": "Internal Server Error"}, 500
    finally:
        db.close()

    return "", 204
