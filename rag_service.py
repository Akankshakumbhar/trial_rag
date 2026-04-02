from __future__ import annotations

import logging
import uuid
from typing import Any, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sqlalchemy.orm import Session

from app import config
from app.models.document import Document
from app.services.text_extraction import extract_text

logger = logging.getLogger(__name__)

_embedder = None
_reranker = None
_qdrant: Optional[QdrantClient] = None


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        if config.QDRANT_URL:
            _qdrant = QdrantClient(url=config.QDRANT_URL)
        else:
            from pathlib import Path

            Path(config.QDRANT_PATH).mkdir(parents=True, exist_ok=True)
            _qdrant = QdrantClient(path=config.QDRANT_PATH)
    return _qdrant


def _ensure_collection(client: QdrantClient) -> None:
    name = config.QDRANT_COLLECTION
    cols = client.get_collections().collections
    if any(c.name == name for c in cols):
        return
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=config.EMBEDDING_DIMS,
            distance=Distance.COSINE,
        ),
    )


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(config.EMBEDDING_MODEL)
    return _embedder


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(config.RERANKER_MODEL)
    return _reranker


def _split_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    return splitter.split_text(text) if text.strip() else []


def index_document(db: Session, document_id: int) -> dict:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError("Document not found")

    text = extract_text(doc.file_path)
    chunks = _split_text(text)
    if not chunks:
        doc.indexed = False
        db.commit()
        return {"document_id": document_id, "chunks_indexed": 0, "message": "No text extracted"}

    embedder = _get_embedder()
    client = _get_qdrant()
    _ensure_collection(client)

    embeddings = embedder.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
    points: List[PointStruct] = []
    for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):
        pid = str(uuid.uuid4())
        points.append(
            PointStruct(
                id=pid,
                vector=vec.tolist(),
                payload={
                    "document_id": doc.id,
                    "chunk_index": i,
                    "text": chunk[:8000],
                    "title": doc.title,
                    "company_name": doc.company_name,
                    "document_type": doc.document_type,
                },
            )
        )

    client.upsert(collection_name=config.QDRANT_COLLECTION, points=points)
    doc.indexed = True
    db.commit()
    return {"document_id": document_id, "chunks_indexed": len(chunks)}


def remove_document_vectors(document_id: int) -> dict:
    client = _get_qdrant()
    _ensure_collection(client)
    client.delete(
        collection_name=config.QDRANT_COLLECTION,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )
    return {"document_id": document_id, "removed": True}


def semantic_search(query: str, top_k: Optional[int] = None) -> List[dict[str, Any]]:
    top_k = top_k or config.RERANK_TOP_K
    vec_k = config.VECTOR_SEARCH_TOP_K

    embedder = _get_embedder()
    client = _get_qdrant()
    _ensure_collection(client)

    qvec = embedder.encode(query, convert_to_numpy=True).tolist()
    hits = client.search(
        collection_name=config.QDRANT_COLLECTION,
        query_vector=qvec,
        limit=vec_k,
        with_payload=True,
    )

    if not hits:
        return []

    pairs = [(query, h.payload.get("text", "") if h.payload else "") for h in hits]
    reranker = _get_reranker()
    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(hits, scores),
        key=lambda x: float(x[1]),
        reverse=True,
    )[:top_k]

    out: List[dict[str, Any]] = []
    for hit, score in ranked:
        p = hit.payload or {}
        out.append(
            {
                "document_id": p.get("document_id"),
                "chunk_index": p.get("chunk_index", 0),
                "text": p.get("text", ""),
                "score": float(score),
                "title": p.get("title"),
                "company_name": p.get("company_name"),
                "document_type": p.get("document_type"),
            }
        )
    return out


def get_document_context(document_id: int) -> List[dict[str, Any]]:
    client = _get_qdrant()
    _ensure_collection(client)

    scroll_filter = Filter(
        must=[
            FieldCondition(
                key="document_id",
                match=MatchValue(value=document_id),
            )
        ]
    )

    results, _ = client.scroll(
        collection_name=config.QDRANT_COLLECTION,
        scroll_filter=scroll_filter,
        limit=500,
        with_payload=True,
        with_vectors=False,
    )

    chunks = []
    for r in results:
        p = r.payload or {}
        chunks.append(
            {
                "chunk_index": p.get("chunk_index", 0),
                "text": p.get("text", ""),
                "title": p.get("title"),
                "company_name": p.get("company_name"),
                "document_type": p.get("document_type"),
            }
        )
    chunks.sort(key=lambda x: x["chunk_index"])
    return chunks
