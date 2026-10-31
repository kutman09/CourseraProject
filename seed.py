"""Idempotent local acceptance fixtures; existing rows are not overwritten."""
from datetime import date
from sqlalchemy import select
from mysite.database.db import Base, engine, SessionLocal
from mysite.database.models import User, Category, Course, StudyGroup
from mysite.api.security import hash_password

TEST_PASSWORD = 'Test12345!'

def seed(db):
    for index, name in enumerate(('Programming', 'Data Science', 'Design'), start=1):
        if not db.get(Category, index):
            db.add(Category(id=index, category_name=name))
    for role in ('admin', 'teacher', 'manager', 'student', 'student_inactive'):
        email = f'{role}@test.kg'
        if not db.scalar(select(User).where(User.email == email)):
            db.add(User(full_name=role, email=email, password=hash_password(TEST_PASSWORD), role='student' if role == 'student_inactive' else role, is_active=role != 'student_inactive'))
    db.flush()
    data = [
        (1, 'Python Basics', 1, 'Python basics from scratch', 'beginner', 0, 8, 'free'),
        (2, 'Python Data Science', 2, 'Pandas, NumPy and machine learning basics', 'intermediate', 7500, 16, 'free'),
        (3, 'Backend FastAPI', 1, 'Backend development', 'advanced', 10000, 12, 'plus'),
        (4, 'Web Design', 3, 'Web design basics', 'beginner', 5000, 10, 'plus'),
    ]
    for pk, title, category, description, level, price, weeks, status in data:
        if not db.get(Course, pk):
            db.add(Course(id=pk, title=title, category_id=category, description=description, level=[level], price=price, duration_weeks=weeks, status=status, is_active=True))
    db.flush()
    teacher = db.scalar(select(User).where(User.email == 'teacher@test.kg'))
    for pk, status in ((1, 'recruiting'), (2, 'completed')):
        if not db.get(StudyGroup, pk):
            db.add(StudyGroup(id=pk, name=f'Python {pk}', course_id=1, teacher_id=teacher.id, starts_on=date(2026, 11, 1), ends_on=date(2027, 2, 1), status=status, capacity=2 if pk == 1 else 20))
    db.commit()

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    print('Seed completed (existing rows preserved).')
