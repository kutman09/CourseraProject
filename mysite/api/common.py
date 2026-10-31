from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

def get_object(db, model, object_id):
    obj = db.get(model, object_id)
    if obj is None:
        raise HTTPException(404, 'Маалымат табылган жок')
    return obj

def save(db, obj):
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Маалымат кайталанды же байланыш бар') from None
    db.refresh(obj)
    return obj

def remove(db, obj):
    db.delete(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Байланышкан маалымат бар') from None
    return {'message': 'Маалымат өчүрүлдү'}
