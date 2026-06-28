"""
Three-Dimensional Temporal Weighting Engine

Implements the core Sophimatic innovation: weighting memory retrieval by BOTH
chronological recency AND experiential significance.

From "The Sovereign Prosthesis":
"A conversation from three years ago that articulated a foundational commitment
may dramatically outrank a casual exchange from yesterday."

Axes:
  Alpha (α) — Experiential significance (four-dimension SMS beta score)
  Beta (β)  — Chronological recency (gated by session type)
  Gamma (γ) — Citation velocity (rolling 30/90-day retrieval frequency)

Spec refinements (Sophimatics Unified Memory Architecture v1.0):
  - Alpha now uses the four-dimension SMS weighted average instead of a
    single importance flag.
  - Beta recency bonus applies only to GENERATIVE and SYNTHETIC sessions;
    creative works (importance >= 8) are recency-immune.
  - Gamma adjusts the combined weight based on citation frequency:
    +0.1 bonus if retrieved 10+ times in 30 days,
    -0.1 penalty if zero retrievals in 90 days.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class WeightedDocument:
    """A document with all three temporal dimensions calculated."""
    content: str
    doc_id: str
    metadata: Dict

    # Raw scores
    importance_score: float  # 0-10 experiential significance
    chronological_age_days: float

    # Calculated weights
    experiential_weight: float
    chronological_weight: float
    gamma_adjustment: float   # Citation velocity delta (+0.1 / 0.0 / -0.1)
    combined_weight: float

    # Retrieval context
    similarity_score: float  # Base RAG similarity
    session_type: str = ""   # SessionType value if known


_RECENCY_ELIGIBLE_SESSION_TYPES: Set[str] = {"GENERATIVE", "SYNTHETIC"}
_RECENCY_IMMUNE_IMPORTANCE_FLOOR: float = 8.0  # Creative works: no recency penalty


class TemporalWeightingEngine:
    """
    Calculates three-dimensional temporal weights for RAG retrieval.

    Axes:
      Alpha (α) — Experiential significance (SMS beta score)
      Beta (β)  — Chronological recency (session-type gated)
      Gamma (γ) — Citation velocity (rolling window)

    Tuning parameters allow shifting the balance:
    - alpha: weight given to experiential significance (default: 0.6)
    - beta: weight given to chronological recency (default: 0.4)
    - decay_rate: how fast chronological relevance fades (default: 0.1)
    """

    def __init__(
        self,
        alpha: float = 0.6,  # Experiential weight - defaults high per paper
        beta: float = 0.4,   # Chronological weight
        decay_rate: float = 0.1,  # Slower decay preserves old foundational docs
        importance_floor: float = 0.1,  # Minimum weight for unrated docs
    ):
        self.alpha = alpha
        self.beta = beta
        self.decay_rate = decay_rate
        self.importance_floor = importance_floor

        # Normalize weights
        total = self.alpha + self.beta
        self.alpha = self.alpha / total
        self.beta = self.beta / total

    def calculate_experiential_weight(self, importance_score: float) -> float:
        """
        Convert 0-10 importance score to weight.

        Non-linear: 10/10 documents are MUCH more important than 5/10.
        Uses exponential scaling to reflect that foundational documents
        should dominate retrieval when relevant.
        """
        # Normalize to 0-1 range
        normalized = importance_score / 10.0

        # Exponential scaling: 10/10 -> 1.0, 5/10 -> 0.25, 1/10 -> 0.01
        # This reflects that a 10/10 foundational document should
        # dramatically outrank casual conversation
        return max(self.importance_floor, normalized ** 2)

    def calculate_chronological_weight(
        self,
        age_days: float,
        session_type: str = "",
        importance_score: float = 5.0,
    ) -> float:
        """
        Calculate recency weight with gradual decay, gated by session type.

        Spec refinements:
        - Recency bonus only applies to GENERATIVE and SYNTHETIC sessions.
        - Creative works (importance >= 8) are recency-immune (return 1.0).
        - TRANSACTIONAL and ADMINISTRATIVE sessions get no recency bonus.
        """
        # Creative works are recency-immune — a play from 2019 is as current as today
        if importance_score >= _RECENCY_IMMUNE_IMPORTANCE_FLOOR:
            return 1.0

        # Non-eligible session types get a flat low weight rather than recency decay
        if session_type and session_type not in _RECENCY_ELIGIBLE_SESSION_TYPES:
            return 0.3  # Stable floor; no recency bonus

        weight = math.exp(-self.decay_rate * age_days / 30)  # Monthly scale
        return max(0.01, weight)  # Floor to prevent total disappearance

    def calculate_combined_weight(
        self,
        similarity: float,
        importance_score: float,
        age_days: float,
        session_type: str = "",
        gamma_delta: float = 0.0,
    ) -> Tuple[float, float, float, float]:
        """
        Calculate final weight combining all three dimensions.

        Returns: (combined_weight, experiential_weight, chronological_weight, gamma_adjustment)

        Gamma delta is the citation-velocity adjustment from memory_tiers.gamma_adjustment().
        """
        exp_weight = self.calculate_experiential_weight(importance_score)
        chron_weight = self.calculate_chronological_weight(
            age_days, session_type, importance_score
        )

        temporal_factor = (self.alpha * exp_weight) + (self.beta * chron_weight)
        combined = similarity * (0.5 + 0.5 * temporal_factor)

        # Apply Gamma axis adjustment, clamped to [0, 1]
        combined = max(0.0, min(1.0, combined + gamma_delta * similarity))

        return combined, exp_weight, chron_weight, gamma_delta

    def weight_documents(
        self,
        documents: List[Dict],
        reference_date: Optional[datetime] = None,
        session_type: str = "",
        gamma_fn=None,
    ) -> List[WeightedDocument]:
        """
        Apply three-dimensional weighting to a list of retrieved documents.

        Expected document format:
        {
            'content': str,
            'id': str,
            'metadata': {
                'importance_score': float (0-10),
                'date': str (ISO format) or datetime,
                'session_type': str (optional),
                ...
            },
            'similarity': float (0-1)
        }

        Args:
            gamma_fn: Optional callable(doc_id) -> float for Gamma axis.
                      If None, Gamma adjustment is 0.0.
        """
        if reference_date is None:
            reference_date = datetime.now()

        weighted = []

        for doc in documents:
            content = doc.get('content', '')
            doc_id = doc.get('id', '')
            metadata = doc.get('metadata', {})
            similarity = doc.get('similarity', 0.5)

            # Support both schemas
            importance = metadata.get('importance_score') or metadata.get('significance_weight', 5.0)

            # Session type: arg takes priority, then metadata
            stype = session_type or metadata.get('session_type', '')

            # Calculate age
            doc_date = metadata.get('date') or metadata.get('timestamp')
            if doc_date:
                if isinstance(doc_date, str):
                    try:
                        doc_date = datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
                    except ValueError:
                        doc_date = reference_date - timedelta(days=30)
                age_days = (reference_date - doc_date).days
            elif 'days_old' in metadata:
                age_days = float(metadata.get('days_old', 30))
            else:
                age_days = 30

            # Gamma axis
            gamma_delta = gamma_fn(doc_id) if gamma_fn and doc_id else 0.0

            combined, exp_w, chron_w, gamma_adj = self.calculate_combined_weight(
                similarity, importance, age_days, stype, gamma_delta
            )

            weighted.append(WeightedDocument(
                content=content,
                doc_id=doc_id,
                metadata=metadata,
                importance_score=importance,
                chronological_age_days=age_days,
                experiential_weight=exp_w,
                chronological_weight=chron_w,
                gamma_adjustment=gamma_adj,
                combined_weight=combined,
                similarity_score=similarity,
                session_type=stype,
            ))

        weighted.sort(key=lambda x: x.combined_weight, reverse=True)
        return weighted

    def rerank_for_query(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 10,
        reference_date: Optional[datetime] = None,
        session_type: str = "",
        gamma_fn=None,
    ) -> List[WeightedDocument]:
        """
        Rerank retrieved documents using Sophimatic three-dimensional weighting.

        This is the main entry point for RAG integration.
        Takes basic similarity-ranked results and applies temporal reranking
        across Alpha (experiential), Beta (chronological), and Gamma (citation
        velocity) axes.
        """
        weighted = self.weight_documents(
            documents, reference_date, session_type=session_type, gamma_fn=gamma_fn
        )
        return weighted[:top_k]

    def explain_ranking(self, doc: WeightedDocument) -> str:
        """
        Generate human-readable explanation of why a document ranked where it did.
        """
        exp_contribution = self.alpha * doc.experiential_weight
        chron_contribution = self.beta * doc.chronological_weight

        lines = [
            f"Document: {doc.doc_id[:50]}...",
            f"  Base similarity: {doc.similarity_score:.3f}",
            f"  Importance (0-10): {doc.importance_score}",
            f"  Age: {doc.chronological_age_days:.0f} days",
            f"  Session type: {doc.session_type or 'unknown'}",
            f"  α Experiential weight: {doc.experiential_weight:.3f} (contributes {exp_contribution:.3f})",
            f"  β Chronological weight: {doc.chronological_weight:.3f} (contributes {chron_contribution:.3f})",
            f"  γ Citation velocity adj: {doc.gamma_adjustment:+.3f}",
            f"  Combined weight: {doc.combined_weight:.3f}",
        ]

        if doc.importance_score >= 8:
            lines.append("  [FOUNDATIONAL] Recency-immune — high experiential significance")
        elif doc.chronological_age_days < 7:
            lines.append("  [RECENT] Fresh temporal relevance")
        if doc.gamma_adjustment > 0:
            lines.append("  [HIGH VELOCITY] Frequently retrieved — Gamma bonus applied")
        elif doc.gamma_adjustment < 0:
            lines.append("  [LOW VELOCITY] Zero retrievals in 90 days — Gamma penalty applied")

        return "\n".join(lines)
