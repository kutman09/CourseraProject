from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from mysite.database.db import get_db
from mysite.database.models import Course, User, Category
from mysite.database.schema import CourseInputSchema, CourseOutSchema
from .deps import require_roles
from .common import get_object, save, remove

course_router = APIRouter(prefix='/course', tags=['Course'])

@course_router.get('/', response_model=list[CourseOutSchema])
def listing(db: Session = Depends(get_db)):
    return db.scalars(select(Course).order_by(Course.id)).all()

@course_router.get('/{object_id}/', response_model=CourseOutSchema)
def detail(object_id: int, db: Session = Depends(get_db)):
    return get_object(db, Course, object_id)

@course_router.post('/', response_model=CourseOutSchema, status_code=201)
def create(body: CourseInputSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('teacher'))):
    get_object(db, Category, body.category_id)
    return save(db, Course(**body.model_dump(mode='json')))

@course_router.put('/{object_id}/', response_model=CourseOutSchema)
def update(object_id: int, body: CourseInputSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('teacher'))):
    obj = get_object(db, Course, object_id)
    get_object(db, Category, body.category_id)
    for key, value in body.model_dump(mode='json').items():
        setattr(obj, key, value)
    return save(db, obj)

@course_router.delete('/{object_id}/')
def delete(object_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('teacher'))):
    return remove(db, get_object(db, Course, object_id))
