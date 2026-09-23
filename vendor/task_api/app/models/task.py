from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column, relationship
from sqlalchemy import DateTime, String, ForeignKey, func
from enum import Enum
from datetime import datetime

from app.models.base import Base

# Task status is restricted to predefined workflow states to ensure data consistency.
class Status(Enum):
    TO_DO = "To-Do"
    IN_PROGRESS = "In Progress"
    COMPLETE = "Complete"

# Task priority is restricted to predefined workflow states to ensure data consistency.
class Priority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str|None] = mapped_column(String(128))
    status: Mapped[Status] = mapped_column(String, nullable=False)
    priority: Mapped[Priority] = mapped_column(String, nullable=False)
    due_date: Mapped[datetime|None] = mapped_column(DateTime) # DateTime enables selection of a time of day functionality

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, 
                                                 server_default=func.now()
                                                 )
    updated_at: Mapped[datetime] = mapped_column(DateTime, 
                                                 server_default=func.now(),
                                                 onupdate=func.now()
                                                 )

    # !r calls repr() on the object instead of str().
    user: Mapped["User"] = relationship("User", back_populates="tasks") # pyright: ignore[reportUndefinedVariable]
    
    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, user_id={self.user_id!r}, title={self.title!r}, description={self.description!r})"