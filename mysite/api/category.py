from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from mysite.database.db import get_db
from mysite.database.models import Category, User
from mysite.database.schema import CategoryInputSchema, CategoryOutSchema
from .deps import require_roles
from .common import get_object, save, remove

category_router = APIRouter(prefix='/category', tags=['Category'])

@category_router.get('/', response_model=list[CategoryOutSchema])
def listing(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.id)).all()

@category_router.get('/{object_id}/', response_model=CategoryOutSchema)
def detail(object_id: int, db: Session = Depends(get_db)):
    return get_object(db, Category, object_id)

@category_router.post('/', response_model=CategoryOutSchema, status_code=201)
def create(body: CategoryInputSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    return save(db, Category(**body.model_dump(mode='json')))

@category_router.put('/{object_id}/', response_model=CategoryOutSchema)
def update(object_id: int, body: CategoryInputSchema, db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    obj = get_object(db, Category, object_id)
    for key, value in body.model_dump(mode='json').items():
        setattr(obj, key, value)
    return save(db, obj)

@category_router.delete('/{object_id}/')
def delete(object_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    return remove(db, get_object(db, Category, object_id))
