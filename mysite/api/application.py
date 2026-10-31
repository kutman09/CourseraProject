from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from mysite.database.db import get_db
from mysite.database.models import Application, User, Course
from mysite.database.schema import ApplicationInputSchema, ApplicationUpdateSchema, ApplicationOutSchema
from .deps import require_roles
from .common import get_object, save, remove

application_router = APIRouter(prefix='/application', tags=['Application'])

def can_student_apply(student, course) -> bool:
    return student.is_active or course.status == 'free'

@application_router.post('/', response_model=ApplicationOutSchema, status_code=201)
def create(body: ApplicationInputSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('student'))):
    course = get_object(db, Course, body.course_id)
    if not course.is_active:
        raise HTTPException(400, 'Курс активдүү эмес')
    if not can_student_apply(user, course):
        raise HTTPException(403, 'Уруксат жок')
    duplicate = db.scalar(select(Application).where(Application.student_id == user.id, Application.course_id == course.id, Application.status.in_(['new', 'in_progress'])))
    if duplicate:
        raise HTTPException(400, 'Заявка мурун берилген')
    return save(db, Application(**body.model_dump(), student_id=user.id))

@application_router.get('/', response_model=list[ApplicationOutSchema])
def listing(db: Session = Depends(get_db), user: User = Depends(require_roles('manager'))):
    return db.scalars(select(Application).order_by(Application.id)).all()

@application_router.get('/{application_id}/', response_model=ApplicationOutSchema)
def detail(application_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('manager'))):
    return get_object(db, Application, application_id)

@application_router.put('/{application_id}/', response_model=ApplicationOutSchema)
def update(application_id: int, body: ApplicationUpdateSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('manager'))):
    obj = get_object(db, Application, application_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    obj.manager_id = user.id
    return save(db, obj)

@application_router.delete('/{application_id}/')
def delete(application_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('manager'))):
    return remove(db, get_object(db, Application, application_id))
