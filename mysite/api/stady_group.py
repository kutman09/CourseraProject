from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from mysite.database.db import get_db
from mysite.database.models import StudyGroup, Course, User, Enrollment
from mysite.database.schema import StudyGroupInputSchema, StudyGroupOutSchema
from .deps import require_roles
from .common import get_object, save, remove

group_router = APIRouter(prefix='/group', tags=['StudyGroup'])

def group_data(db, body, user):
    get_object(db, Course, body.course_id)
    teacher_id = body.teacher_id if user.role == 'admin' else user.id
    if teacher_id is None:
        raise HTTPException(400, 'Мугалимди тандаңыз')
    teacher = get_object(db, User, teacher_id)
    if teacher.role != 'teacher':
        raise HTTPException(400, 'Колдонуучу мугалим эмес')
    return {**body.model_dump(), 'teacher_id': teacher_id}

def check_owner(obj, user):
    if user.role != 'admin' and obj.teacher_id != user.id:
        raise HTTPException(403, 'Уруксат жок')

@group_router.get('/', response_model=list[StudyGroupOutSchema])
def listing(db: Session = Depends(get_db)):
    return db.scalars(select(StudyGroup).order_by(StudyGroup.id)).all()

@group_router.get('/{group_id}/', response_model=StudyGroupOutSchema)
def detail(group_id: int, db: Session = Depends(get_db)):
    return get_object(db, StudyGroup, group_id)

@group_router.post('/', response_model=StudyGroupOutSchema, status_code=201)
def create(body: StudyGroupInputSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('teacher'))):
    return save(db, StudyGroup(**group_data(db, body, user)))

@group_router.put('/{group_id}/', response_model=StudyGroupOutSchema)
def update(group_id: int, body: StudyGroupInputSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('teacher'))):
    obj = get_object(db, StudyGroup, group_id)
    check_owner(obj, user)
    count = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.group_id == group_id, Enrollment.status == 'active'))
    if body.capacity < count:
        raise HTTPException(400, 'Орундардын саны жетишсиз')
    for key, value in group_data(db, body, user).items():
        setattr(obj, key, value)
    return save(db, obj)

@group_router.delete('/{group_id}/')
def delete(group_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('teacher'))):
    obj = get_object(db, StudyGroup, group_id)
    check_owner(obj, user)
    return remove(db, obj)
