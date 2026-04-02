# UserCreate / UserLogin → request bodies; UserResponse → API output.
# from_attributes lets Pydantic read SQLAlchemy model instances (Pydantic v2).
from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    email: str
    password: str
    company_name: str | None = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    company_name: str | None = None
