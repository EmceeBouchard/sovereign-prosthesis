"""WikiSophimaticsEngine — wiki corpus integration with Sophimatics metadata.

Connects a Karpathy-style personal wiki architecture to the Sophimatics
temporal weighting engine. Each wiki entry receives Sophimatics metadata:
importance scores, temporal status, and disposition classification.

Described in The Sovereign Prosthesis as the bridge between external
knowledge structures and the Ur-Codex's longitudinal personal record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .temporal_weighting import MemoryCandidate, TemporalWeightingEngine, TemporalScore


class Disposition(str, Enum):
    SETTLED = "settled"         # claim is stable; low retrieval priority
    ACTIVE = "active"           # claim is under active development
    CONTESTED = "contested"     # claim is in dispute; high retrieval priority
    SUPERSEDED = "superseded"   # claim has been replaced
    ARCHIVED = "archived"       # claim is historical record only


@dataclass
class WikiEntry:
    title: str
    content: str
    importance: float           # [0, 1] — caller-assigned significance
    disposition: Disposition = Disposition.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = field(default_factory=list)
    linked_titles: list[str] = field(default_factory=list)
    entry_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entry_id:
            self.entry_id = self._slug(self.title)
        self.linked_titles = self._extract_links(self.content)

    @staticmethod
    def _slug(title: str) -> str:
        return re.sub(r"[^a-z0-9_]", "_", title.lower().strip())

    @staticmethod
    def _extract_links(content: str) -> list[str]:
        return re.findall(r"\[\[([^\]]+)\]\]", content)


@dataclass
class ScoredWikiEntry:
    entry: WikiEntry
    temporal_score: TemporalScore


class WikiSophimaticsEngine:
    """Integrates a personal wiki with Sophimatics temporal scoring.

    Wiki entries are treated as MemoryCandidates and scored on the
    two-dimensional temporal manifold (alpha=0.6, beta=0.4). Disposition
    modifies effective importance: contested entries score higher;
    superseded and archived entries score lower.
    """

    DISPOSITION_MODIFIERS: dict[Disposition, float] = {
        Disposition.SETTLED: 0.9,
        Disposition.ACTIVE: 1.0,
        Disposition.CONTESTED: 1.15,
        Disposition.SUPERSEDED: 0.4,
        Disposition.ARCHIVED: 0.2,
    }

    def __init__(self, weighting_engine: TemporalWeightingEngine | None = None) -> None:
        self._engine = weighting_engine or TemporalWeightingEngine()
        self._entries: dict[str, WikiEntry] = {}

    def add(self, entry: WikiEntry) -> None:
        self._entries[entry.entry_id] = entry

    def add_many(self, entries: list[WikiEntry]) -> None:
        for e in entries:
            self.add(e)

    def score_entry(self, entry: WikiEntry) -> ScoredWikiEntry:
        modifier = self.DISPOSITION_MODIFIERS.get(entry.disposition, 1.0)
        effective_importance = min(1.0, entry.importance * modifier)

        candidate = MemoryCandidate(
            entry_id=entry.entry_id,
            timestamp=entry.updated_at,
            significance=effective_importance,
        )
        score = self._engine.score(candidate)
        return ScoredWikiEntry(entry=entry, temporal_score=score)

    def rank_all(
        self,
        top_k: int | None = None,
        disposition_filter: list[Disposition] | None = None,
    ) -> list[ScoredWikiEntry]:
        """Return all wiki entries ranked by composite Sophimatics score."""
        entries = list(self._entries.values())
        if disposition_filter:
            entries = [e for e in entries if e.disposition in disposition_filter]

        scored = [self.score_entry(e) for e in entries]
        ranked = sorted(scored, key=lambda s: s.temporal_score.composite, reverse=True)
        return ranked[:top_k] if top_k is not None else ranked

    def get(self, entry_id: str) -> WikiEntry | None:
        return self._entries.get(entry_id)

    def linked_to(self, title: str) -> list[WikiEntry]:
        """Return all entries that link to the given title."""
        slug = WikiEntry._slug(title)
        return [
            e for e in self._entries.values()
            if slug in [WikiEntry._slug(t) for t in e.linked_titles]
        ]

    def contested(self) -> list[WikiEntry]:
        return [e for e in self._entries.values() if e.disposition == Disposition.CONTESTED]
