from pydantic import BaseModel

class AssignRole(BaseModel):
    user_id: int
    role_id: int