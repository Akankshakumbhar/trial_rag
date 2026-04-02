from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DocumentType = Literal["invoice", "report", "contract"]


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    document_type: DocumentType


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company_name: str
    document_type: str
    uploaded_by: int
    created_at: datetime
    original_filename: str
    mime_type: Optional[str] = None
    indexed: bool


class DocumentSearchParams(BaseModel):
    title: Optional[str] = None
    company_name: Optional[str] = None
    document_type: Optional[str] = None
    uploaded_by: Optional[int] = None
