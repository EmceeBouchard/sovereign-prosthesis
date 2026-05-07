"""
Two-Dimensional Temporal Weighting Engine

Implements the core Sophimatic innovation: weighting memory retrieval by BOTH
chronological recency AND experiential significance.

From "The Sovereign Prosthesis":
"A conversation from three years ago that articulated a foundational commitment
may dramatically outrank a casual exchange from yesterday."

The Importance Index (0-10) provides the experiential dimension.
Chronological decay provides the temporal dimension.
The weighted combination respects the phenomenology of personal relevance.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class WeightedDocument:
    """A document with both temporal dimensions calculated."""
    content: str
    doc_id: str
    metadata: Dict

    # Raw scores
    importance_score: float  # 0-10 experiential significance
    chronological_age_days: float

    # Calculated weights
    experiential_weight: float
    chronological_weight: float
    combined_weight: float

    # Retrieval context
    similarity_score: float  # Base RAG similarity


class TemporalWeightingEngine:
    """
    Calculates two-dimensional temporal weights for RAG retrieval.

    The key insight: chronological time and experiential time are orthogonal.
    A document's relevance = f(similarity, chronological_recency, experiential_significance)

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

    def calculate_chronological_weight(self, age_days: float) -> float:
        """
        Calculate recency weight with gradual decay.

        Uses exponential decay but with a slow rate, reflecting that
        in Sophimatic terms, a 3-year-old foundational document
        shouldn't be penalized heavily for age alone.
        """
        # Exponential decay: recent = 1.0, old = lower
        # With decay_rate=0.1, half-life is about 7 days
        # But experiential significance can override this
        weight = math.exp(-self.decay_rate * age_days / 30)  # Monthly scale
        return max(0.01, weight)  # Floor to prevent total disappearance

    def calculate_combined_weight(
        self,
        similarity: float,
        importance_score: float,
        age_days: float
    ) -> Tuple[float, float, float]:
        """
        Calculate final weight combining all dimensions.

        Returns: (combined_weight, experiential_weight, chronological_weight)
        """
        exp_weight = self.calculate_experiential_weight(importance_score)
        chron_weight = self.calculate_chronological_weight(age_days)

        # The combined weight respects both dimensions
        # Similarity remains primary (you still need semantic relevance)
        # But temporal dimensions modulate the ranking
        temporal_factor = (self.alpha * exp_weight) + (self.beta * chron_weight)

        # Combined: similarity * temporal modulation
        # This means a 10/10 old document can outrank a 1/10 recent one
        combined = similarity * (0.5 + 0.5 * temporal_factor)

        return combined, exp_weight, chron_weight

    def weight_documents(
        self,
        documents: List[Dict],
        reference_date: Optional[datetime] = None
    ) -> List[WeightedDocument]:
        """
        Apply two-dimensional weighting to a list of retrieved documents.

        Expected document format:
        {
            'content': str,
            'id': str,
            'metadata': {
                'importance_score': float (0-10),
                'date': str (ISO format) or datetime,
                ...
            },
            'similarity': float (0-1)
        }
        """
        if reference_date is None:
            reference_date = datetime.now()

        weighted = []

        for doc in documents:
            # Extract fields
            content = doc.get('content', '')
            doc_id = doc.get('id', '')
            metadata = doc.get('metadata', {})
            similarity = doc.get('similarity', 0.5)

            # Get importance score (default to mid-range if not rated)
            importance = metadata.get('importance_score', 5.0)

            # Calculate age
            doc_date = metadata.get('date')
            if doc_date:
                if isinstance(doc_date, str):
                    try:
                        doc_date = datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
                    except ValueError:
                        doc_date = reference_date - timedelta(days=30)  # Default to month old
                age_days = (reference_date - doc_date).days
            else:
                age_days = 30  # Default assumption

            # Calculate weights
            combined, exp_w, chron_w = self.calculate_combined_weight(
                similarity, importance, age_days
            )

            weighted.append(WeightedDocument(
                content=content,
                doc_id=doc_id,
                metadata=metadata,
                importance_score=importance,
                chronological_age_days=age_days,
                experiential_weight=exp_w,
                chronological_weight=chron_w,
                combined_weight=combined,
                similarity_score=similarity
            ))

        # Sort by combined weight descending
        weighted.sort(key=lambda x: x.combined_weight, reverse=True)

        return weighted

    def rerank_for_query(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 10,
        reference_date: Optional[datetime] = None
    ) -> List[WeightedDocument]:
        """
        Rerank retrieved documents using Sophimatic weighting.

        This is the main entry point for RAG integration.
        Takes basic similarity-ranked results and applies
        two-dimensional temporal reranking.
        """
        weighted = self.weight_documents(documents, reference_date)
        return weighted[:top_k]

    def explain_ranking(self, doc: WeightedDocument) -> str:
        """
        Generate human-readable explanation of why a document ranked where it did.

        Useful for debugging and transparency about the Sophimatic process.
        """
        exp_contribution = self.alpha * doc.experiential_weight
        chron_contribution = self.beta * doc.chronological_weight

        lines = [
            f"Document: {doc.doc_id[:50]}...",
            f"  Base similarity: {doc.similarity_score:.3f}",
            f"  Importance (0-10): {doc.importance_score}",
            f"  Age: {doc.chronological_age_days:.0f} days",
            f"  Experiential weight: {doc.experiential_weight:.3f} (contributes {exp_contribution:.3f})",
            f"  Chronological weight: {doc.chronological_weight:.3f} (contributes {chron_contribution:.3f})",
            f"  Combined weight: {doc.combined_weight:.3f}"
        ]

        if doc.importance_score >= 8:
            lines.append("  [FOUNDATIONAL] High experiential significance")
        elif doc.chronological_age_days < 7:
            lines.append("  [RECENT] Fresh temporal relevance")

        return "\n".join(lines)
