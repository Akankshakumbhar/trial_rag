from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user_mgmt import UserPermissionsOut, UserRolesOut
from app.schemas.user_role import AssignRole
from app.utils.db import get_db
from app.utils.dependencies import (
    check_permission,
    get_current_user,
    get_user_role_names,
    user_has_permission,
)
from app.utils.permissions import ROLE_PERMISSIONS

router = APIRouter(prefix="/users", tags=["users"])


def _ensure_self_or_admin(current_user: User, user_id: int, db: Session) -> None:
    if current_user.id == user_id:
        return
    names = get_user_role_names(db, current_user.id)
    if not user_has_permission(names, "all"):
        raise HTTPException(status_code=403, detail="Not allowed to access this user")


def _aggregate_permissions(role_names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for rn in role_names:
        for p in ROLE_PERMISSIONS.get(rn, []):
            if p not in seen:
                seen.add(p)
                out.append(p)
    return sorted(out)


@router.post("/assign-role")
def assign_role(
    data: AssignRole,
    _: bool = Depends(check_permission("manage_roles")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    existing = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == data.user_id,
            UserRole.role_id == data.role_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Role already assigned")

    db.add(UserRole(user_id=data.user_id, role_id=data.role_id))
    db.commit()
    return {"message": "Role assigned successfully"}


@router.get("/{user_id}/roles", response_model=UserRolesOut)
def get_user_roles(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_self_or_admin(current_user, user_id, db)
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    roles: list[Role] = []
    for ur in user_roles:
        role = db.query(Role).filter(Role.id == ur.role_id).first()
        if role:
            roles.append(role)
    return UserRolesOut(user_id=user_id, roles=roles)


@router.get("/{user_id}/permissions", response_model=UserPermissionsOut)
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_self_or_admin(current_user, user_id, db)
    role_names = get_user_role_names(db, user_id)
    return UserPermissionsOut(
        user_id=user_id,
        permissions=_aggregate_permissions(role_names),
    )
