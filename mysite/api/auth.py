from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from mysite.database.db import get_db
from mysite.database.models import User
from mysite.database.schema import UserInputSchema, UserOutSchema, LoginSchema, TokenSchema
from .security import hash_password, verify_password, create_access_token
from .common import save

auth_router = APIRouter(prefix='/auth', tags=['Auth'])

@auth_router.post('/register/', response_model=UserOutSchema, status_code=201)
def register(body: UserInputSchema, db: Session = Depends(get_db)):
    email = str(body.email).casefold()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, 'Бул email катталган')
    return save(db, User(full_name=body.full_name, email=email, password=hash_password(body.password), role='student'))

def authenticate(db, email, password):
    user = db.scalar(select(User).where(User.email == email.casefold()))
    if not user or not verify_password(password, user.password):
        raise HTTPException(401, 'Email же сырсөз туура эмес', headers={'WWW-Authenticate': 'Bearer'})
    return {'access_token': create_access_token(user.id), 'token_type': 'bearer'}

@auth_router.post('/login/', response_model=TokenSchema)
def login(body: LoginSchema, db: Session = Depends(get_db)):
    return authenticate(db, str(body.email), body.password)

@auth_router.post('/token/', response_model=TokenSchema)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return authenticate(db, form.username, form.password)
