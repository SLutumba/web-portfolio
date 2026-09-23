from app.models.task import Task

def task_serialiser(task: Task):
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date
    }

def tasks_serialiser(tasks: list[Task]):

    serialised_tasks = []
    for task in tasks:
        serialised_tasks.append(task_serialiser(task))

    return serialised_tasks