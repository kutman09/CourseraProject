from datetime import date, datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from .models import (RoleChoices, UserStatusChoices, LevelChoices, CourseStatusChoices,
                     GroupStatusChoices, ApplicationStatusChoices, EnrollmentStatusChoices)

class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid', str_strip_whitespace=True)

Password = Annotated[str, Field(min_length=8, max_length=72)]

class PasswordMixin(Schema):
    @field_validator('password', check_fields=False)
    @classmethod
    def password_bytes(cls, value):
        if value is not None and len(value.encode('utf-8')) > 72:
            raise ValueError('Сырсөз өтө узун')
        return value

class UserInputSchema(PasswordMixin):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: Password

class LoginSchema(Schema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=500)

class TokenSchema(Schema):
    access_token: str
    token_type: str = 'bearer'

class UserOutSchema(Schema):
    id: int
    full_name: str
    email: EmailStr
    role: RoleChoices
    user_status: UserStatusChoices
    is_active: bool

class UserUpdateSchema(PasswordMixin):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    password: Password | None = None

class UserAdminUpdateSchema(Schema):
    role: RoleChoices | None = None
    user_status: UserStatusChoices | None = None
    is_active: bool | None = None

class CategoryInputSchema(Schema):
    category_name: str = Field(min_length=1, max_length=50)

class CategoryOutSchema(CategoryInputSchema):
    id: int

class CourseInputSchema(Schema):
    title: str = Field(min_length=1, max_length=200)
    category_id: int
    description: str
    level: list[LevelChoices] = Field(min_length=1, max_length=3)
    price: float = Field(default=0, ge=0, allow_inf_nan=False)
    duration_weeks: int = Field(gt=0)
    is_active: bool = True
    status: CourseStatusChoices = CourseStatusChoices.free

class CourseOutSchema(CourseInputSchema):
    id: int
    created_at: datetime
    updated_at: datetime

class StudyGroupInputSchema(Schema):
    name: str = Field(min_length=1, max_length=100)
    course_id: int
    teacher_id: int | None = None
    starts_on: date
    ends_on: date
    status: GroupStatusChoices = GroupStatusChoices.recruiting
    capacity: int = Field(default=20, gt=0)

    @model_validator(mode='after')
    def dates(self):
        if self.ends_on <= self.starts_on:
            raise ValueError('Бүтүү күнү башталган күндөн кийин болсун')
        return self

class StudyGroupOutSchema(StudyGroupInputSchema):
    id: int
    teacher_id: int

class ApplicationInputSchema(Schema):
    course_id: int
    comment: str | None = None

class ApplicationUpdateSchema(Schema):
    status: ApplicationStatusChoices
    comment: str | None = None

class ApplicationOutSchema(ApplicationInputSchema):
    id: int
    student_id: int
    manager_id: int | None = None
    status: ApplicationStatusChoices

class EnrollmentInputSchema(Schema):
    group_id: int

class EnrollmentUpdateSchema(Schema):
    status: EnrollmentStatusChoices

class EnrollmentOutSchema(EnrollmentInputSchema):
    id: int
    student_id: int
    status: EnrollmentStatusChoices

class SearchSchema(Schema):
    question: str = Field(min_length=1, max_length=500)

class TextSchema(Schema):
    text: str = Field(min_length=1, max_length=5000)

class AnswerSchema(TextSchema):
    facts: str | None = Field(default=None, max_length=5000)
