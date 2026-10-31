import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from mysite.config import settings
from mysite.database.db import get_db
from mysite.database.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/token/', auto_error=False)

def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    error = HTTPException(401, 'Кирүү керек', headers={'WWW-Authenticate': 'Bearer'})
    if not token:
        raise error
    try:
        payload = jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM], options={'require': ['sub', 'exp']})
        user = db.get(User, int(payload['sub']))
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise error from None
    if user is None:
        raise error
    return user

def require_roles(*roles):
    def check(user: User = Depends(get_current_user)):
        if user.role != 'admin' and user.role not in roles:
            raise HTTPException(403, 'Уруксат жок')
        return user
    return check
