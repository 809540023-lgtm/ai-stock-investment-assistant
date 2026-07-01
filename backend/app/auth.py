from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證身分",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise cred_exc
    user = db.get(User, user_id)
    if user is None:
        raise cred_exc
    return user


def _admin_emails() -> set[str]:
    return {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}


def is_admin_user(user: User) -> bool:
    return bool(getattr(user, "is_admin", False)) or user.email.lower() in _admin_emails()


def promote_if_admin_email(user: User, db: Session) -> None:
    """登入/註冊時，若 email 在 ADMIN_EMAILS 名單且尚未標記，補上 is_admin。"""
    if not user.is_admin and user.email.lower() in _admin_emails():
        user.is_admin = True
        db.commit()
        db.refresh(user)


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """管理端 API 用：需 is_admin 或在 ADMIN_EMAILS 名單內，否則 403。"""
    if not is_admin_user(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理員權限")
    return user
