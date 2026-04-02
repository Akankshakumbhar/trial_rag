from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config
from app.database import Base, SessionLocal, engine
from app.models.document import Document
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.routes.auth import router as auth_router
from app.routes.documents import router as documents_router
from app.routes.rag import router as rag_router
from app.routes.roles import router as roles_router
from app.routes.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        role_seed = [
            ("Admin", "Full access"),
            ("Financial Analyst", "Upload and edit documents"),
            ("Auditor", "Review documents"),
            ("Client", "View company documents"),
        ]
        for name, desc in role_seed:
            if not db.query(Role).filter(Role.name == name).first():
                db.add(Role(name=name, description=desc))
        db.commit()

        if config.INITIAL_ADMIN_EMAIL:
            user = (
                db.query(User)
                .filter(User.email == config.INITIAL_ADMIN_EMAIL)
                .first()
            )
            admin_role = db.query(Role).filter(Role.name == "Admin").first()
            if user and admin_role:
                existing = (
                    db.query(UserRole)
                    .filter(
                        UserRole.user_id == user.id,
                        UserRole.role_id == admin_role.id,
                    )
                    .first()
                )
                if not existing:
                    db.add(UserRole(user_id=user.id, role_id=admin_role.id))
                    db.commit()
    finally:
        db.close()

    yield


app = FastAPI(
    title="Financial Document Management",
    description="Document management with semantic (RAG) search and RBAC",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(roles_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(rag_router)


@app.get("/")
def root():
    return {"message": "API is running"}
