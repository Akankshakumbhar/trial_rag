import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import config
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services import rag_service
from app.utils.db import get_db
from app.utils.dependencies import (
    can_access_document,
    check_permission,
    get_current_user,
    get_user_role_names,
    is_client_only_scoped,
)
router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = frozenset({"invoice", "report", "contract"})


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    company_name: str = Form(...),
    document_type: str = Form(...),
    _: bool = Depends(check_permission("upload")),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dt = document_type.strip().lower()
    if dt not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"document_type must be one of: {', '.join(sorted(ALLOWED_TYPES))}",
        )

    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    user_dir = config.UPLOAD_DIR / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename or "upload").name
    stored = f"{uuid.uuid4().hex}_{safe_name}"
    dest = user_dir / stored

    try:
        with open(dest, "wb") as out:
            shutil.copyfileobj(file.file, out)
    finally:
        await file.close()

    doc = Document(
        title=title.strip(),
        company_name=company_name.strip(),
        document_type=dt,
        uploaded_by=current_user.id,
        file_path=str(dest.resolve()),
        original_filename=safe_name,
        mime_type=file.content_type,
        indexed=False,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _apply_metadata_filters(q, title, company_name, document_type, uploaded_by):
    if title:
        q = q.filter(Document.title.ilike(f"%{title}%"))
    if company_name:
        q = q.filter(Document.company_name.ilike(f"%{company_name}%"))
    if document_type:
        q = q.filter(Document.document_type == document_type.strip().lower())
    if uploaded_by is not None:
        q = q.filter(Document.uploaded_by == uploaded_by)
    return q


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role_names = get_user_role_names(db, current_user.id)
    if not role_names:
        raise HTTPException(status_code=403, detail="No roles assigned")

    q = db.query(Document)
    if is_client_only_scoped(role_names):
        if not current_user.company_name:
            return []
        q = q.filter(Document.company_name == current_user.company_name)
    docs = q.order_by(Document.created_at.desc()).all()
    return [d for d in docs if can_access_document(current_user, d, role_names)]


@router.get("/search", response_model=list[DocumentResponse])
def search_documents(
    title: Optional[str] = None,
    company_name: Optional[str] = None,
    document_type: Optional[str] = None,
    uploaded_by: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role_names = get_user_role_names(db, current_user.id)
    if not role_names:
        raise HTTPException(status_code=403, detail="No roles assigned")
    q = db.query(Document)
    q = _apply_metadata_filters(q, title, company_name, document_type, uploaded_by)
    if is_client_only_scoped(role_names):
        if not current_user.company_name:
            return []
        q = q.filter(Document.company_name == current_user.company_name)
    docs = q.order_by(Document.created_at.desc()).all()
    return [d for d in docs if can_access_document(current_user, d, role_names)]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    role_names = get_user_role_names(db, current_user.id)
    if not can_access_document(current_user, doc, role_names):
        raise HTTPException(status_code=403, detail="Not allowed to access this document")
    return doc


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    _: bool = Depends(check_permission("delete")),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    role_names = get_user_role_names(db, current_user.id)
    if not can_access_document(current_user, doc, role_names):
        raise HTTPException(status_code=403, detail="Not allowed to delete this document")

    try:
        rag_service.remove_document_vectors(document_id)
    except Exception:
        pass

    path = doc.file_path
    db.delete(doc)
    db.commit()
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
    return {"message": "Document deleted", "document_id": document_id}
