from .db import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Enum, Date, ForeignKey, Text, Boolean, DateTime, Float, JSON, CheckConstraint
from typing import Optional, List
from enum import Enum as PyEnum
from datetime import date, datetime, timezone


def utc_now():
    return datetime.now(timezone.utc)


class RoleChoices(str, PyEnum):
    student = "student"
    teacher = "teacher"
    manager = "manager"
    admin = "admin"


class UserStatusChoices(str, PyEnum):
    free = "free"
    pro = "pro"


class LevelChoices(str, PyEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class CourseStatusChoices(str, PyEnum):
    free = "free"
    plus = "plus"


class GroupStatusChoices(str, PyEnum):
    recruiting = "recruiting"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class ApplicationStatusChoices(str, PyEnum):
    new = "new"
    in_progress = "in_progress"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"


class EnrollmentStatusChoices(str, PyEnum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(String)
    role: Mapped[RoleChoices] = mapped_column(Enum(RoleChoices), default=RoleChoices.student)
    user_status: Mapped[UserStatusChoices] = mapped_column(Enum(UserStatusChoices), default=UserStatusChoices.free)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    teacher_groups: Mapped[List['StudyGroup']] = relationship(back_populates='teacher')
    student_applications: Mapped[List['Application']] = relationship(
        back_populates='student', foreign_keys='Application.student_id')
    manager_applications: Mapped[List['Application']] = relationship(
        back_populates='manager', foreign_keys='Application.manager_id')
    enrollments: Mapped[List['Enrollment']] = relationship(back_populates='student', cascade='all,delete-orphan')


class Category(Base):
    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String(50), unique=True)

    courses: Mapped[List['Course']] = relationship(back_populates='category', cascade='all,delete-orphan')


class Course(Base):
    __tablename__ = 'course'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[int] = mapped_column(ForeignKey('category.id'))
    description: Mapped[str] = mapped_column(Text)
    level: Mapped[List[str]] = mapped_column(JSON, default=lambda: [LevelChoices.beginner.value])
    price: Mapped[float] = mapped_column(Float, default=0)
    duration_weeks: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[CourseStatusChoices] = mapped_column(Enum(CourseStatusChoices), default=CourseStatusChoices.free)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    category: Mapped[Category] = relationship(back_populates='courses')
    groups: Mapped[List['StudyGroup']] = relationship(back_populates='course', cascade='all,delete-orphan')
    applications: Mapped[List['Application']] = relationship(back_populates='course', cascade='all,delete-orphan')


class StudyGroup(Base):
    __tablename__ = 'study_group'
    __table_args__ = (CheckConstraint('capacity > 0', name='positive_group_capacity'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capacity: Mapped[int] = mapped_column(Integer, default=20)
    name: Mapped[str] = mapped_column(String(100))
    course_id: Mapped[int] = mapped_column(ForeignKey('course.id'))
    teacher_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    status: Mapped[GroupStatusChoices] = mapped_column(Enum(GroupStatusChoices), default=GroupStatusChoices.recruiting)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    course: Mapped[Course] = relationship(back_populates='groups')
    teacher: Mapped[User] = relationship(back_populates='teacher_groups')
    enrollments: Mapped[List['Enrollment']] = relationship(back_populates='group', cascade='all,delete-orphan')


class Application(Base):
    __tablename__ = 'application'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    course_id: Mapped[int] = mapped_column(ForeignKey('course.id'))
    manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey('user.id'), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ApplicationStatusChoices] = mapped_column(
        Enum(ApplicationStatusChoices), default=ApplicationStatusChoices.new)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    student: Mapped[User] = relationship(back_populates='student_applications', foreign_keys=[student_id])
    manager: Mapped[Optional[User]] = relationship(back_populates='manager_applications', foreign_keys=[manager_id])
    course: Mapped[Course] = relationship(back_populates='applications')


class Enrollment(Base):
    __tablename__ = 'enrollment'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    group_id: Mapped[int] = mapped_column(ForeignKey('study_group.id'))
    status: Mapped[EnrollmentStatusChoices] = mapped_column(
        Enum(EnrollmentStatusChoices), default=EnrollmentStatusChoices.active)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    student: Mapped[User] = relationship(back_populates='enrollments')
    group: Mapped[StudyGroup] = relationship(back_populates='enrollments')
