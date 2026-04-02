from typing import List, Optional

from pydantic import BaseModel, Field


class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(
        default=None,
        description="Final results after reranking; default from config",
    )


class RagSearchChunk(BaseModel):
    document_id: int
    chunk_index: int
    text: str
    score: float
    title: Optional[str] = None
    company_name: Optional[str] = None
    document_type: Optional[str] = None


class RagSearchResponse(BaseModel):
    query: str
    chunks: List[RagSearchChunk]


class IndexDocumentRequest(BaseModel):
    document_id: int
