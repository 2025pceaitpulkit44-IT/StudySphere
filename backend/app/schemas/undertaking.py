from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UndertakingIn(BaseModel):
    institution: str = Field(min_length=2, max_length=200)
    faculty_name: str = Field(min_length=2, max_length=120)
    designation: str = Field(min_length=2, max_length=120)
    email: EmailStr
    department: str = Field(min_length=2, max_length=120)
    authorization_type: Literal["owner", "permission"]
    accepted: bool


class UndertakingRecord(BaseModel):
    institution: str
    faculty_name: str
    designation: str
    email: str
    department: str
    authorization_type: str
    accepted_at: datetime


class UndertakingStatus(BaseModel):
    completed: bool
    declaration: str
    record: UndertakingRecord | None = None
