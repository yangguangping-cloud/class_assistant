from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


# Grade schemas
class GradeBase(BaseModel):
    name: str


class GradeCreate(GradeBase):
    pass


class GradeUpdate(GradeBase):
    pass


class GradeResponse(GradeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Subject schemas
class SubjectBase(BaseModel):
    name: str


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(SubjectBase):
    pass


class SubjectResponse(SubjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseModel):
    username: str
    name: str
    subject_id: Optional[int] = None
    role: str = "teacher"
    avatar: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


# Class schemas
class ClassBase(BaseModel):
    name: str
    display_name: Optional[str] = None
    grade_id: int
    teacher_id: int


class ClassCreate(ClassBase):
    pass


class ClassUpdate(ClassBase):
    pass


class ClassResponse(ClassBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Tag schemas - Moved before Student schemas
class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class TagUpdate(TagBase):
    pass


class TagResponse(TagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Student schemas
class StudentBase(BaseModel):
    name: str
    gender: str
    birthday: Optional[date] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    hobbies: Optional[str] = None
    friends: Optional[str] = None
    class_id: int
    active: bool = True


class StudentCreate(StudentBase):
    pass


class StudentUpdate(StudentBase):
    pass


class StudentResponse(BaseModel):
    id: int
    name: str
    gender: str
    birthday: Optional[date] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    hobbies: Optional[str] = None
    friends: Optional[str] = None
    class_id: int
    active: bool = True
    created_at: datetime
    tags: List[dict] = []


# Score schemas
class ScoreBase(BaseModel):
    student_id: int
    class_id: int
    subject_id: int
    score_type: str
    score: float
    exam_date: date


class ScoreCreate(ScoreBase):
    pass


class ScoreResponse(ScoreBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Schedule schemas
class ScheduleBase(BaseModel):
    class_id: int
    teacher_id: int
    subject_id: int
    day_of_week: int
    time_slot: str
    start_time: str
    end_time: str


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(ScheduleBase):
    pass


class ScheduleResponse(ScheduleBase):
    id: int
    created_at: datetime
    class_name: Optional[str] = None
    teacher_name: Optional[str] = None
    subject_name: Optional[str] = None

    class Config:
        from_attributes = True
