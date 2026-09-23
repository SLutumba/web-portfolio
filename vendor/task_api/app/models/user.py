from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column, relationship
from sqlalchemy import DateTime, String, func
from datetime import datetime

from app.models.base import Base

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, 
                                                 server_default=func.now()
                                                 )
    updated_at: Mapped[datetime] = mapped_column(DateTime, 
                                                 server_default=func.now(),
                                                 onupdate=func.now()
                                                 )

    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="user") # pyright: ignore[reportUndefinedVariable]

    # __repr__ returns an unambiguous string representation of a User instance,
    # making debugging and logging much easier.
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, username={self.username!r}, email={self.email!r})"