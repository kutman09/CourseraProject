from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from mysite.database.db import get_db
from mysite.database.models import Enrollment, StudyGroup, User
from mysite.database.schema import EnrollmentInputSchema, EnrollmentUpdateSchema, EnrollmentOutSchema
from .deps import get_current_user, require_roles
from .common import get_object, save, remove

enrollment_router = APIRouter(prefix='/enrollment', tags=['Enrollment'])

def get_enrollment_queryset(db, user):
    query = select(Enrollment)
    if user.role == 'student':
        query = query.where(Enrollment.student_id == user.id)
    elif user.role == 'teacher':
        query = query.join(StudyGroup).where(StudyGroup.teacher_id == user.id)
    elif user.role not in ('manager', 'admin'):
        raise HTTPException(403, 'Уруксат жок')
    return query

def visible_enrollment(db, user, enrollment_id):
    obj = db.scalar(get_enrollment_queryset(db, user).where(Enrollment.id == enrollment_id))
    if obj is None:
        raise HTTPException(404, 'Мындай жазылуу жок')
    return obj

def lock_enrollments(db):
    # Release authentication's read transaction, then serialize SQLite writers.
    db.commit()
    if db.get_bind().dialect.name == 'sqlite':
        db.execute(text('BEGIN IMMEDIATE'))

def check_admission(db, user, group_id, exclude_id=None):
    group = get_object(db, StudyGroup, group_id)
    if group.status != 'recruiting':
        raise HTTPException(400, 'Группага кабыл алуу жабык')
    active = select(Enrollment).where(Enrollment.group_id == group_id, Enrollment.status == 'active')
    if exclude_id is not None:
        active = active.where(Enrollment.id != exclude_id)
    if db.scalar(active.where(Enrollment.student_id == user.id)):
        raise HTTPException(400, 'Сиз мурун жазылгансыз')
    count = db.scalar(select(func.count()).select_from(active.subquery()))
    if count >= group.capacity:
        raise HTTPException(400, 'Группа толгон')

@enrollment_router.post('/', response_model=EnrollmentOutSchema, status_code=201)
def create(body: EnrollmentInputSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('student'))):
    lock_enrollments(db)
    # Use the same scoped query for duplicate detection in creation as for reads.
    existing = db.scalar(get_enrollment_queryset(db, user).where(Enrollment.group_id == body.group_id, Enrollment.student_id == user.id, Enrollment.status == 'active'))
    if existing:
        raise HTTPException(400, 'Сиз мурун жазылгансыз')
    check_admission(db, user, body.group_id)
    return save(db, Enrollment(group_id=body.group_id, student_id=user.id))

@enrollment_router.get('/', response_model=list[EnrollmentOutSchema])
def listing(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(get_enrollment_queryset(db, user).order_by(Enrollment.id)).all()

@enrollment_router.get('/{enrollment_id}/', response_model=EnrollmentOutSchema)
def detail(enrollment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return visible_enrollment(db, user, enrollment_id)

@enrollment_router.put('/{enrollment_id}/', response_model=EnrollmentOutSchema)
def update(enrollment_id: int, body: EnrollmentUpdateSchema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lock_enrollments(db)
    obj = visible_enrollment(db, user, enrollment_id)
    if user.role == 'student' and body.status != 'cancelled':
        raise HTTPException(403, 'Жазылууну гана жокко чыгарсаңыз болот')
    if body.status == 'active' and obj.status != 'active':
        check_admission(db, obj.student, obj.group_id, obj.id)
    obj.status = body.status
    return save(db, obj)

@enrollment_router.delete('/{enrollment_id}/')
def delete(enrollment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return remove(db, visible_enrollment(db, user, enrollment_id))
