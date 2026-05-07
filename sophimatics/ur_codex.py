"""UrCodexManager — longitudinal corpus management via ChromaDB.

Implements the Ur-Codex described in Section 2 of The Sovereign Prosthesis.
The Ur-Codex is the persistent, user-specific corpus whose accumulation
across interactions crosses the prosthesis threshold (Clark & Chalmers).
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False


@dataclass
class CodexEntry:
    content: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class RetrievalResult:
    entry_id: str
    content: str
    source: str
    distance: float
    metadata: dict[str, Any]


class UrCodexManager:
    """Manages the user's longitudinal corpus — the Ur-Codex.

    The Ur-Codex is not a session cache. It is the accumulated record of a
    user's intellectual history: conversations, documents, reflections, and
    projects. Its persistence across time is what enables proximal integration
    and distinguishes AII from stateless cloud AI.
    """

    COLLECTION_NAME = "ur_codex"
    DEFAULT_CHUNK_SIZE = 512
    DEFAULT_CHUNK_OVERLAP = 64

    def __init__(self, persist_directory: str = "./codex_store") -> None:
        self.persist_directory = persist_directory
        self._collection = None
        self._client = None

        if not _CHROMA_AVAILABLE:
            raise ImportError(
                "chromadb is required: pip install chromadb"
            )

        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def ingest(self, entry: CodexEntry) -> str:
        """Add a single entry to the Ur-Codex."""
        chunks = self._chunk(entry.content)
        ids, documents, metadatas = [], [], []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{entry.entry_id}_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "entry_id": entry.entry_id,
                "source": entry.source,
                "timestamp": entry.timestamp.isoformat(),
                "chunk_index": i,
                "chunk_count": len(chunks),
                "content_hash": entry.content_hash(),
                **entry.metadata,
            })

        self._collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return entry.entry_id

    def ingest_many(self, entries: list[CodexEntry]) -> list[str]:
        return [self.ingest(e) for e in entries]

    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve relevant entries by semantic similarity."""
        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": min(n_results, self._collection.count() or 1),
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        output = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            output.append(RetrievalResult(
                entry_id=meta.get("entry_id", ""),
                content=doc,
                source=meta.get("source", ""),
                distance=results["distances"][0][i],
                metadata=meta,
            ))
        return output

    def count(self) -> int:
        return self._collection.count()

    def _chunk(
        self,
        text: str,
        size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> list[str]:
        if len(text) <= size:
            return [text]
        chunks, start = [], 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append(text[start:end])
            start += size - overlap
        return chunks
