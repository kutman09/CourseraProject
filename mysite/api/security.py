from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from mysite.config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('ascii')

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('ascii'))
    except (ValueError, UnicodeError):
        return False

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(user_id), 'iat': now, 'exp': now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)}, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)
