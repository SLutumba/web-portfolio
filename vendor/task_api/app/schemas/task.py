from pydantic import BaseModel, Field, field_validator
from app.models.task import Status, Priority
from datetime import datetime, timezone

class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=3, max_length=64)
    description: str|None = Field(default=None, max_length=128)
    status: Status
    priority: Priority
    due_date: datetime|None = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, title: str) -> str:
        if (title is None or 
            title.strip() == "" or
            len(title.strip()) < 3):
            raise ValueError(
                'Title cannot be blank or less than 3 characters'
            )
        return title

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, due_date: datetime) -> datetime:
        if due_date is None:
            return None
        if (due_date.tzinfo is None or 
            due_date.tzinfo.utcoffset(due_date) is None
        ):
            raise ValueError(
                'Due date must contain timezone information.'
            )

        return due_date.astimezone(timezone.utc) # Normalised due date to ensure data consistency


class UpdateTaskRequest(BaseModel):
    title: str|None = Field(default=None, max_length=64)
    description: str|None = Field(default=None, max_length=128)
    status: Status|None = None
    priority: Priority|None = None
    due_date: datetime|None = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, title: str) -> str:
        if (title is None or 
            title.strip() == "" or
            len(title.strip()) < 3):
            raise ValueError(
                'Title cannot be blank or less than 3 characters'
            )
        return title

    @field_validator('status')
    @classmethod
    def validate_status(cls, status: Status) -> Status:
        if status is None:
            raise ValueError(
                'Status cannot be blank'
            )
        return status

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, priority: Priority) -> Priority:
        if priority is None:
            raise ValueError(
                'Priority cannot be blank'
            )
        return priority

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, due_date: datetime) -> datetime:
        if due_date is None:
            return None
        if (due_date.tzinfo is None or 
            due_date.tzinfo.utcoffset(due_date) is None
        ):
            raise ValueError(
                'Due date must contain timezone information.'
            )

        return due_date.astimezone(timezone.utc) # Normalised due date to ensure data consistency