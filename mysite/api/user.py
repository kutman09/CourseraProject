from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from mysite.database.db import get_db
from mysite.database.models import User
from mysite.database.schema import UserOutSchema, UserUpdateSchema, UserAdminUpdateSchema
from .deps import get_current_user, require_roles
from .security import hash_password
from .common import get_object, save

user_router = APIRouter(prefix='/users', tags=['Users'])

@user_router.get('/me/', response_model=UserOutSchema)
def me(user: User = Depends(get_current_user)):
    return user

@user_router.put('/me/', response_model=UserOutSchema)
def update_me(body: UserUpdateSchema, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for key, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user, key, hash_password(value) if key == 'password' else value)
    return save(db, user)

@user_router.get('/', response_model=list[UserOutSchema])
def users(db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    return db.scalars(select(User).order_by(User.id)).all()

@user_router.get('/{user_id}/', response_model=UserOutSchema)
def detail(user_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    return get_object(db, User, user_id)

@user_router.put('/{user_id}/', response_model=UserOutSchema)
def update(user_id: int, body: UserAdminUpdateSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    obj = get_object(db, User, user_id)
    for key, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(obj, key, value)
    return save(db, obj)
