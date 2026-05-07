"""TemporalWeightingEngine — two-dimensional temporal manifold.

Implements the Sophimatic temporal weighting described in Section 3 of
The Sovereign Prosthesis. Memory is scored on two orthogonal axes:

  alpha (α = 0.6) — experiential significance: how important was this
                     moment to the user's cognitive trajectory?
  beta  (β = 0.4) — chronological recency: how recently did it occur?

These axes are independent. A highly significant but distant memory
outscores a trivial recent one. The composite score determines retrieval
priority in the Ur-Codex.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence


ALPHA = 0.6  # experiential significance weight
BETA = 0.4   # chronological recency weight
DECAY_HALFLIFE_DAYS = 90.0  # recency half-life


@dataclass
class TemporalScore:
    """Composite temporal score for a single memory entry."""
    entry_id: str
    significance: float       # raw significance [0, 1]
    recency: float            # computed recency [0, 1]
    composite: float          # alpha*significance + beta*recency
    days_elapsed: float

    def __lt__(self, other: TemporalScore) -> bool:
        return self.composite < other.composite


@dataclass
class MemoryCandidate:
    entry_id: str
    timestamp: datetime
    significance: float  # caller-supplied, [0, 1]


class TemporalWeightingEngine:
    """Scores memory candidates on the two-dimensional Sophimatic manifold.

    Usage::

        engine = TemporalWeightingEngine()
        scores = engine.score_many(candidates)
        top = sorted(scores, reverse=True)[:10]
    """

    def __init__(
        self,
        alpha: float = ALPHA,
        beta: float = BETA,
        decay_halflife_days: float = DECAY_HALFLIFE_DAYS,
    ) -> None:
        if not math.isclose(alpha + beta, 1.0, rel_tol=1e-6):
            raise ValueError(f"alpha + beta must equal 1.0, got {alpha + beta}")
        self.alpha = alpha
        self.beta = beta
        self.decay_halflife_days = decay_halflife_days
        self._lambda = math.log(2) / decay_halflife_days

    def score(
        self,
        candidate: MemoryCandidate,
        reference_time: datetime | None = None,
    ) -> TemporalScore:
        """Compute the composite temporal score for a single candidate."""
        now = reference_time or datetime.now(timezone.utc)
        ts = candidate.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        days_elapsed = max(0.0, (now - ts).total_seconds() / 86400.0)
        recency = math.exp(-self._lambda * days_elapsed)
        composite = self.alpha * candidate.significance + self.beta * recency

        return TemporalScore(
            entry_id=candidate.entry_id,
            significance=candidate.significance,
            recency=recency,
            composite=composite,
            days_elapsed=days_elapsed,
        )

    def score_many(
        self,
        candidates: Sequence[MemoryCandidate],
        reference_time: datetime | None = None,
    ) -> list[TemporalScore]:
        now = reference_time or datetime.now(timezone.utc)
        return [self.score(c, reference_time=now) for c in candidates]

    def rank(
        self,
        candidates: Sequence[MemoryCandidate],
        top_k: int | None = None,
        reference_time: datetime | None = None,
    ) -> list[TemporalScore]:
        """Return candidates ranked by composite score, descending."""
        scores = self.score_many(candidates, reference_time=reference_time)
        ranked = sorted(scores, reverse=True)
        return ranked[:top_k] if top_k is not None else ranked
