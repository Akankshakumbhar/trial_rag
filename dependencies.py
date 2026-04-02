from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.utils.db import get_db
from app.utils.permissions import ROLE_PERMISSIONS
from app.utils.security import ALGORITHM, SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_user_role_names(db: Session, user_id: int) -> list[str]:
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    names: list[str] = []
    for r in user_roles:
        role = db.query(Role).filter(Role.id == r.role_id).first()
        if role:
            names.append(role.name)
    return names


def user_has_permission(role_names: list[str], required_permission: str) -> bool:
    for role_name in role_names:
        perms = ROLE_PERMISSIONS.get(role_name, [])
        if "all" in perms or required_permission in perms:
            return True
    return False


def is_client_only_scoped(role_names: list[str]) -> bool:
    if user_has_permission(role_names, "all"):
        return False
    if "Financial Analyst" in role_names or "Analyst" in role_names or "Auditor" in role_names:
        return False
    return "Client" in role_names


def can_access_document(user: User, doc: Document, role_names: list[str]) -> bool:
    if user_has_permission(role_names, "all"):
        return True
    if "Financial Analyst" in role_names or "Analyst" in role_names:
        return True
    if "Auditor" in role_names:
        return True
    if "Client" in role_names and user_has_permission(role_names, "view"):
        return bool(user.company_name) and doc.company_name == user.company_name
    return False


def check_permission(required_permission: str):
    def permission_dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> bool:
        role_names = get_user_role_names(db, user.id)
        if user_has_permission(role_names, required_permission):
            return True
        raise HTTPException(status_code=403, detail="Permission denied")

    return permission_dependency
