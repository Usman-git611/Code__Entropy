from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.settings import settings

# PBKDF2-SHA256 is a salted, deliberately slow password hash and avoids the
# current bcrypt/Passlib compatibility issue on Python 3.14.
pwd = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
oauth2 = OAuth2PasswordBearer(tokenUrl='/api/auth/login')
def hash_password(password: str): return pwd.hash(password)
def verify_password(password: str, hashed: str): return pwd.verify(password, hashed)
def create_token(user: User):
    return jwt.encode({'sub': user.id, 'role': user.role, 'exp': datetime.now(timezone.utc)+timedelta(minutes=settings.access_token_minutes)}, settings.secret_key, algorithm='HS256')
def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    try: payload = jwt.decode(token, settings.secret_key, algorithms=['HS256']); user_id = payload.get('sub')
    except JWTError: user_id = None
    user = db.get(User, user_id) if user_id else None
    if not user: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Please sign in again.')
    return user
def require_role(*roles):
    def check(user: User = Depends(current_user)):
        if user.role not in roles: raise HTTPException(403, 'You do not have access to this area.')
        return user
    return check
