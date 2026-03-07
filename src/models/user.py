from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


class UserBase(SQLModel):
    email: Optional[str] = Field(default=None, unique=True)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # Relationships
    tasks: List["Task"] = Relationship(back_populates="user")
    conversations: List["Conversation"] = Relationship(back_populates="user")


class UserRead(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime


class UserCreate(UserBase):
    pass