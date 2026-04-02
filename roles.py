from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.role import Role
from app.schemas.role import RoleCreate, RoleResponse
from app.utils.db import get_db
from app.utils.dependencies import check_permission

router = APIRouter(prefix="/roles", tags=["roles"])


@router.post("/create", response_model=RoleResponse)
def create_role(
    role: RoleCreate,
    _: bool = Depends(check_permission("manage_roles")),
    db: Session = Depends(get_db),
):
    db_role = db.query(Role).filter(Role.name == role.name).first()
    if db_role:
        raise HTTPException(status_code=400, detail="Role already exists")
    new_role = Role(name=role.name, description=role.description)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role
