import importlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import main
import seed as seed_module
from mysite.database.db import Base, get_db
from mysite.database.models import User, StudyGroup, Enrollment, Application
from mysite.api.security import hash_password, create_access_token

@pytest.fixture(scope='session')
def password_hash():
    return hash_password('Test12345!')

@pytest.fixture
def context(monkeypatch, password_hash):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def fk(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(seed_module, 'hash_password', lambda _: password_hash)
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(importlib.import_module('mysite.admin.setup'), 'SessionLocal', factory)
    with factory() as db:
        seed_module.seed(db)
        users = {u.email.split('@')[0]: u.id for u in db.scalars(select(User))}
        other_teacher = User(full_name='Other teacher', email='other_teacher@test.kg', password=password_hash, role='teacher')
        db.add(other_teacher)
        db.flush()
        db.get(StudyGroup, 2).teacher_id = other_teacher.id
        db.add_all([Enrollment(id=1, student_id=users['student'], group_id=1),
                    Enrollment(id=2, student_id=users['student_inactive'], group_id=2),
                    Application(id=1, student_id=users['student'], course_id=1)])
        db.commit()
        users['other_teacher'] = other_teacher.id
    def override():
        with factory() as db:
            yield db
    main.app.dependency_overrides[get_db] = override
    headers = {role: {'Authorization': f'Bearer {create_access_token(pk)}'} for role, pk in users.items()}
    headers['anonymous'] = {}
    with TestClient(main.app) as client:
        yield client, factory, headers, users
    main.app.dependency_overrides.clear()
    engine.dispose()
