from datetime import datetime

from pydantic import BaseModel


class SubjectOut(BaseModel):
    id: int
    code: str
    name: str
    department: str
    semester: int
    units: int


class VersionOut(BaseModel):
    version_number: int
    original_filename: str
    size_bytes: int
    status: str
    stage: str
    error_message: str
    is_current: bool
    chunk_count: int
    created_at: datetime


class DocumentOut(BaseModel):
    id: int
    title: str
    subject: SubjectOut
    material_type: str
    topic: str
    unit: str
    department: str
    semester: int
    academic_year: str
    status: str
    stage: str
    error_message: str
    version: int            # newest version number
    chunk_count: int        # chunks of the live (current) version
    uploader_name: str
    original_filename: str
    created_at: datetime
    versions: list[VersionOut] = []
