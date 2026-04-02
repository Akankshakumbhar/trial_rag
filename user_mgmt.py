from pydantic import BaseModel, ConfigDict

from app.schemas.role import RoleResponse


class UserRolesOut(BaseModel):
    user_id: int
    roles: list[RoleResponse]


class UserPermissionsOut(BaseModel):
    user_id: int
    permissions: list[str]
