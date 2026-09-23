from sqlalchemy.orm import Session
from app.exceptions import InvalidDateTimeError, TaskNotFoundError
from app.models import Task
from app.schemas.task import CreateTaskRequest, UpdateTaskRequest
from datetime import datetime, timezone

def create_task(
        db: Session,
        request: CreateTaskRequest,
        user_id: int
    ) -> Task:

    if (request.due_date is not None 
        and (request.due_date < datetime.now(timezone.utc))):
        raise InvalidDateTimeError(
            f"Invalid due date entered. The date cannot be before today's date: {datetime.today().date()}"
        )
    new_task = Task(
        user_id=user_id,
        title=request.title,
        description=request.description,
        status=request.status.value,
        priority=request.priority.value,
        due_date=request.due_date
    )

    db.add(new_task)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(new_task)

    return new_task

def get_tasks(
        db: Session,
        user_id: int
    ) -> list[Task]:

    # query the db for all tasks that have the specified user id. 
    tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .all()
    )
    
    return tasks

def get_task(
        db: Session, 
        user_id: int, 
        task_id: int
    ) -> Task:

    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id)
        .first()
    )

    if task is None:
        raise TaskNotFoundError(
            "Task doesn't exist"
        )

    return task

def update_task(
        db: Session, 
        request: UpdateTaskRequest,
        task_id: int,
        user_id: int
    ):

    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id)
        .first()
    )

    if task is None:
        raise TaskNotFoundError(
            "Task not Found"
        )

    if (request.due_date is not None 
        and (request.due_date < datetime.now(timezone.utc))):
        raise InvalidDateTimeError(
            f"Invalid due date entered. The date cannot be before today's date: {datetime.today().date()}"
        )

    payload = request.model_dump(exclude_unset=True)   
    task.title = (
        request.title 
        if "title" in payload 
        and request.title is not None
        else task.title
        )
    task.description = (
        request.description 
        if "description" in payload 
        else task.description
        )
    task.status = (
        request.status.value 
        if "status" in payload
        and request.status is not None
        else task.status
        )
    task.priority = (
        request.priority.value 
        if "priority" in payload 
        and request.priority is not None
        else task.priority
        )
    task.due_date = (
        request.due_date 
        if "due_date" in  payload 
        else task.due_date
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(task)

    return task

def delete_task(
        db: Session,
        task_id: int, 
        user_id: int
        ):

    task = (
        db.query(Task)
        .filter(Task.user_id == user_id, 
                Task.id == task_id)
        .first())

    if task is None:
        raise TaskNotFoundError(
            "Task not found"
        )

    db.delete(task)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise