"""
Provenance Tracker: Memory vs. Inference vs. Speculation

From "The Sovereign Prosthesis":
"What did it find? What did it infer? What did it speculate?
The difference matters—to Michael, who has staked a philosophical
position on the matter."

This module implements:
1. Tagging claims by epistemic status (memory, inference, speculation)
2. Confidence calibration for retrieved information
3. Transparency about the source and certainty of knowledge
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class EpistemicStatus(Enum):
    """The provenance category for a piece of information."""
    MEMORY = "memory"           # Directly retrieved from Ur-Codex
    INFERENCE = "inference"     # Derived from multiple sources
    SPECULATION = "speculation" # Generated without direct support
    SYNTHESIS = "synthesis"     # Combined from retrieval + reasoning
    EXTERNAL = "external"       # From external sources (web, papers)


class ConfidenceLevel(Enum):
    """Calibrated confidence in information accuracy."""
    HIGH = "high"           # Direct quote, verified source
    MODERATE = "moderate"   # Strong inference, corroborated
    LOW = "low"             # Reasonable guess, uncorroborated
    SPECULATIVE = "speculative"  # Hypothesis, needs verification


@dataclass
class ProvenanceTag:
    """A provenance marker for a piece of information."""
    status: EpistemicStatus
    confidence: ConfidenceLevel
    sources: List[str]  # Document IDs or source names
    reasoning: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_inline_marker(self) -> str:
        """Generate inline provenance marker for response text."""
        status_markers = {
            EpistemicStatus.MEMORY: "[M]",
            EpistemicStatus.INFERENCE: "[I]",
            EpistemicStatus.SPECULATION: "[S]",
            EpistemicStatus.SYNTHESIS: "[Y]",
            EpistemicStatus.EXTERNAL: "[E]"
        }
        return status_markers.get(self.status, "[?]")

    def to_explanation(self) -> str:
        """Generate human-readable provenance explanation."""
        source_str = ", ".join(self.sources[:3])
        if len(self.sources) > 3:
            source_str += f" (+{len(self.sources) - 3} more)"

        explanations = {
            EpistemicStatus.MEMORY: f"Retrieved from: {source_str}",
            EpistemicStatus.INFERENCE: f"Inferred from: {source_str}",
            EpistemicStatus.SPECULATION: "Speculative—no direct source",
            EpistemicStatus.SYNTHESIS: f"Synthesized from: {source_str}",
            EpistemicStatus.EXTERNAL: f"External source: {source_str}"
        }
        return explanations.get(self.status, "Unknown provenance")


class ProvenanceTracker:
    """
    Tracks and tags the epistemic provenance of information.

    The core function: maintain transparency about what the system
    knows vs. infers vs. speculates. This is philosophically important
    to the user and operationally important for trust calibration.
    """

    def __init__(self):
        # Tracking for current session
        self.session_claims: List[Dict] = []

        # Thresholds for classification
        self.memory_confidence_threshold = 0.8  # Similarity for "memory"
        self.inference_threshold = 0.5  # Below this = speculation

    def classify_retrieval(
        self,
        query: str,
        retrieved_docs: List[Dict],
        similarity_threshold: float = 0.7
    ) -> Tuple[EpistemicStatus, ConfidenceLevel, List[str]]:
        """
        Classify the epistemic status of information based on retrieval results.

        High similarity = memory (direct retrieval)
        Moderate similarity = inference (supported but indirect)
        Low/no similarity = speculation (no direct support)
        """
        if not retrieved_docs:
            return EpistemicStatus.SPECULATION, ConfidenceLevel.SPECULATIVE, []

        # Get best matches
        top_docs = sorted(
            retrieved_docs,
            key=lambda x: x.get('similarity', 0),
            reverse=True
        )[:3]

        best_similarity = top_docs[0].get('similarity', 0) if top_docs else 0
        sources = [doc.get('id', 'unknown') for doc in top_docs]

        # Classify based on similarity
        if best_similarity >= self.memory_confidence_threshold:
            return EpistemicStatus.MEMORY, ConfidenceLevel.HIGH, sources
        elif best_similarity >= similarity_threshold:
            return EpistemicStatus.INFERENCE, ConfidenceLevel.MODERATE, sources
        elif best_similarity >= self.inference_threshold:
            return EpistemicStatus.INFERENCE, ConfidenceLevel.LOW, sources
        else:
            return EpistemicStatus.SPECULATION, ConfidenceLevel.SPECULATIVE, sources

    def tag_claim(
        self,
        claim: str,
        retrieved_docs: List[Dict],
        is_generated: bool = False
    ) -> ProvenanceTag:
        """
        Generate a provenance tag for a specific claim.
        """
        if is_generated and not retrieved_docs:
            return ProvenanceTag(
                status=EpistemicStatus.SPECULATION,
                confidence=ConfidenceLevel.SPECULATIVE,
                sources=[],
                reasoning="Generated without retrieval support"
            )

        status, confidence, sources = self.classify_retrieval(
            claim, retrieved_docs
        )

        tag = ProvenanceTag(
            status=status,
            confidence=confidence,
            sources=sources,
            reasoning=f"Based on {len(sources)} retrieved documents"
        )

        # Track for session
        self.session_claims.append({
            "claim": claim[:100],
            "tag": tag
        })

        return tag

    def annotate_response(
        self,
        response: str,
        claim_tags: List[Tuple[str, ProvenanceTag]]
    ) -> str:
        """
        Annotate a response with inline provenance markers.

        This makes the epistemic status visible in the output,
        respecting the user's philosophical commitment to transparency.
        """
        annotated = response

        # Add inline markers (subtle)
        for claim, tag in claim_tags:
            if claim in annotated:
                marker = tag.to_inline_marker()
                # Add marker after the claim
                annotated = annotated.replace(
                    claim,
                    f"{claim} {marker}",
                    1  # Only first occurrence
                )

        return annotated

    def generate_provenance_footer(
        self,
        claim_tags: List[Tuple[str, ProvenanceTag]]
    ) -> str:
        """
        Generate a footer explaining provenance markers used.
        """
        if not claim_tags:
            return ""

        # Count by status
        status_counts = {}
        for _, tag in claim_tags:
            status = tag.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        lines = ["---", "Provenance:"]

        for status, count in status_counts.items():
            marker = {
                "memory": "[M]",
                "inference": "[I]",
                "speculation": "[S]",
                "synthesis": "[Y]",
                "external": "[E]"
            }.get(status, "[?]")
            lines.append(f"  {marker} {status}: {count} claims")

        return "\n".join(lines)

    def get_session_summary(self) -> Dict:
        """
        Summarize provenance distribution for current session.
        """
        if not self.session_claims:
            return {"total_claims": 0}

        status_counts = {}
        confidence_counts = {}

        for item in self.session_claims:
            tag = item["tag"]
            status = tag.status.value
            confidence = tag.confidence.value

            status_counts[status] = status_counts.get(status, 0) + 1
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

        return {
            "total_claims": len(self.session_claims),
            "by_status": status_counts,
            "by_confidence": confidence_counts
        }

    def should_hedge(self, tag: ProvenanceTag) -> bool:
        """
        Determine if a claim should be hedged based on provenance.

        Speculative claims should be explicitly marked as such.
        Low confidence inferences should be qualified.
        """
        if tag.status == EpistemicStatus.SPECULATION:
            return True
        if tag.confidence in [ConfidenceLevel.LOW, ConfidenceLevel.SPECULATIVE]:
            return True
        return False

    def get_hedge_phrase(self, tag: ProvenanceTag) -> str:
        """
        Get an appropriate hedging phrase for uncertain claims.
        """
        phrases = {
            (EpistemicStatus.SPECULATION, ConfidenceLevel.SPECULATIVE): [
                "I'm speculating here, but",
                "Without direct evidence,",
                "This is conjecture:",
            ],
            (EpistemicStatus.INFERENCE, ConfidenceLevel.LOW): [
                "Based on limited evidence,",
                "If I'm reading this correctly,",
                "The inference suggests,",
            ],
            (EpistemicStatus.INFERENCE, ConfidenceLevel.MODERATE): [
                "From what I can gather,",
                "The evidence points to",
                "It appears that",
            ]
        }

        key = (tag.status, tag.confidence)
        options = phrases.get(key, ["Possibly,"])
        return options[0]


def is_conversational_response(response: str) -> bool:
    """
    Detect if a response is a simple conversational exchange that
    doesn't require provenance hedging.

    Greetings, acknowledgments, and simple questions don't make
    epistemic claims and shouldn't be tagged as "speculation."
    """
    response_lower = response.lower().strip()

    # Common greeting/conversational patterns
    conversational_patterns = [
        # Greetings
        "hello", "hi ", "hi!", "hey", "good morning", "good afternoon",
        "good evening", "howdy", "greetings",
        # Acknowledgments
        "sure", "okay", "of course", "absolutely", "certainly", "no problem",
        "you're welcome", "happy to help", "glad to help",
        # Questions back to user
        "how can i help", "what can i do", "what would you like",
        "how may i assist", "what do you need",
        # Simple responses
        "thank you", "thanks", "got it", "understood", "i see",
    ]

    # Check if response starts with or is a conversational pattern
    for pattern in conversational_patterns:
        if response_lower.startswith(pattern) or response_lower == pattern:
            return True

    # Very short responses (under 50 chars) that end with ? are likely questions
    if len(response) < 50 and response.strip().endswith("?"):
        return True

    # Very short responses without substantive claims
    if len(response) < 100 and not any(word in response_lower for word in [
        "because", "therefore", "indicates", "suggests", "evidence",
        "according to", "based on", "research", "studies show"
    ]):
        return True

    return False


def create_transparent_response(
    base_response: str,
    retrieved_docs: List[Dict],
    tracker: ProvenanceTracker,
    include_footer: bool = False
) -> str:
    """
    Utility function to create a provenance-transparent response.

    This wraps the common pattern of:
    1. Classifying retrieval quality
    2. Tagging the response
    3. Optionally adding provenance footer

    Note: Simple conversational exchanges (greetings, acknowledgments)
    are exempt from hedging—they don't make epistemic claims.
    """
    # Skip provenance hedging for conversational responses
    if is_conversational_response(base_response):
        return base_response

    # Tag the overall response
    tag = tracker.tag_claim(base_response[:200], retrieved_docs)

    # Hedge if needed
    if tracker.should_hedge(tag):
        hedge = tracker.get_hedge_phrase(tag)
        base_response = f"{hedge} {base_response}"

    # Add footer if requested
    if include_footer:
        footer = tracker.generate_provenance_footer([(base_response[:100], tag)])
        base_response = f"{base_response}\n\n{footer}"

    return base_response
