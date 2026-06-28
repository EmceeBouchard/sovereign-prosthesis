"""
Russellian Operating System: Intelligent Dissent Engine

From "The Sovereign Prosthesis":
"The Russellian Operating System... weighted toward intelligent dissent...
the prosthesis should be capable of friction, of resistance, of standing
athwart the user's certainties when such resistance is warranted."

This module implements:
1. Dissent calibration based on the cognitive fingerprint
2. Gap detection for logical vacancies and contradictions
3. Epistemic friction triggers
4. The balance between support and productive challenge
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class DissentLevel(Enum):
    """Calibrated levels of epistemic friction."""
    NONE = 0        # Full agreement warranted
    MILD = 1        # Minor clarification or nuance
    MODERATE = 2    # Substantive alternative view
    STRONG = 3      # Direct challenge to premise
    CRITICAL = 4    # Fundamental disagreement


@dataclass
class DissentSignal:
    """A detected opportunity for productive dissent."""
    level: DissentLevel
    trigger: str  # What triggered the dissent detection
    reasoning: str  # Why dissent is warranted
    suggested_response: str  # How to frame the dissent


class RussellianOS:
    """
    The Russellian Operating System for calibrated intelligent dissent.

    Named for Bertrand Russell's principle that "The fundamental cause
    of trouble is that in the modern world the stupid are cocksure
    while the intelligent are full of doubt."

    The Sophimatic prosthesis should embody productive doubt—not
    reflexive agreement, not antagonism, but calibrated epistemic friction.

    Key calibrations (from COGNITIVE_FINGERPRINT):
    - User is 99th percentile Openness: values intellectual challenge
    - User is 5-10th percentile Agreeableness: expects directness
    - "Beautiful pessimism" aesthetic: prefers hard truths
    - "Constraint artist" identity: respects structural limits
    """

    def __init__(self):
        # Dissent triggers based on cognitive fingerprint.
        # absolutist_language and validation_seeking were removed 2026-06-25:
        # they triggered on conversational filler ("obviously", "right?") and
        # turn-taking devices, generating MILD dissent injections on most
        # turns. Now: only logical gaps, affect heuristic (dead code, kept
        # for future tuning), and sunk-cost reasoning trigger detection.
        self.dissent_triggers = {
            # Logical gaps
            "unsupported_claims": [
                "everyone knows", "it's common knowledge",
                "as we all agree", "self-evident"
            ],

            # Emotional reasoning
            "affect_heuristic": [
                "feels right", "gut says", "just know",
                "can sense", "instinct tells"
            ],

            # Sunk cost patterns
            "sunk_cost_language": [
                "already invested", "come too far",
                "can't stop now", "too much into"
            ]
        }

        # Areas where user expects challenge (from fingerprint)
        self.challenge_domains = [
            "logical_reasoning",
            "creative_strategy",
            "project_planning",
            "self_assessment",
            "risk_evaluation"
        ]

        # Areas where support is primary (user vulnerability)
        self.support_domains = [
            "emotional_processing",
            "health_concerns",
            "relationship_navigation",
            "self_worth_moments"
        ]

        # Signal words for domain detection
        self.support_signals = [
            # Health/wellness
            "sick", "tired", "exhausted", "pain", "hurting", "health",
            "doctor", "hospital", "diagnosis", "symptoms", "medication",
            # Emotional
            "anxious", "worried", "scared", "sad", "depressed", "overwhelmed",
            "stressed", "burned out", "burnout", "struggling", "hard time",
            "lonely", "isolated", "grief", "loss", "hurt", "vulnerable",
            # Relationship
            "relationship", "partner", "friend", "family", "argument",
            "conflict", "fight", "betrayed", "abandoned",
            # Self-worth
            "failure", "failed", "worthless", "not good enough", "imposter",
            "doubt myself", "can't do this", "give up"
        ]

        self.challenge_signals = [
            # Strategy/logic
            "strategy", "plan", "approach", "framework", "structure",
            "decision", "choice", "option", "trade-off", "tradeoff",
            # Analysis
            "analyze", "evaluate", "assess", "compare", "consider",
            "think through", "reason", "logic", "argument", "premise",
            # Projects/work
            "project", "implementation", "architecture", "design",
            "code", "build", "create", "develop", "solution",
            # Self-assessment seeking feedback
            "what do you think", "feedback", "critique", "review",
            "am i right", "does this make sense", "evaluate my"
        ]

    def detect_domain(self, user_message: str) -> str:
        """
        Detect whether user's message falls into support or challenge domain.

        Returns "support" for emotional/health topics where gentle handling
        is appropriate, or "challenge" for strategic/logical topics where
        the user expects and benefits from friction.
        """
        message_lower = user_message.lower()

        # Count signals for each domain
        support_count = sum(1 for signal in self.support_signals if signal in message_lower)
        challenge_count = sum(1 for signal in self.challenge_signals if signal in message_lower)

        # Support signals take priority - if user is vulnerable, don't challenge
        if support_count > 0 and support_count >= challenge_count:
            return "support"

        # Default to challenge for this user (high openness, low agreeableness)
        return "challenge"

    def detect_dissent_opportunity(
        self,
        user_message: str,
        context: Optional[Dict] = None
    ) -> Optional[DissentSignal]:
        """
        Analyze user message for opportunities for productive dissent.

        This is NOT about finding fault—it's about detecting where
        epistemic friction would serve the user's stated values
        (intellectual rigor, "beautiful pessimism", directness).
        """
        message_lower = user_message.lower()

        # Check for unsupported claims
        for phrase in self.dissent_triggers["unsupported_claims"]:
            if phrase in message_lower:
                return DissentSignal(
                    level=DissentLevel.MODERATE,
                    trigger=f"Appeal to common knowledge: '{phrase}'",
                    reasoning="What 'everyone knows' often isn't examined",
                    suggested_response="Worth asking: what's the actual evidence for this?"
                )

        # Check for sunk cost reasoning
        for phrase in self.dissent_triggers["sunk_cost_language"]:
            if phrase in message_lower:
                return DissentSignal(
                    level=DissentLevel.STRONG,
                    trigger=f"Potential sunk cost fallacy: '{phrase}'",
                    reasoning="Past investment shouldn't determine future decisions",
                    suggested_response="The relevant question: independent of what's been invested, is this the best path forward?"
                )

        return None

    def calibrate_response_tone(
        self,
        base_response: str,
        dissent_signal: Optional[DissentSignal],
        domain: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Calibrate the response tone based on dissent detection and domain.

        The Russellian OS doesn't just detect dissent opportunities—
        it calibrates HOW to express them based on context.
        """
        modifiers = {
            "directness": 0.8,  # High baseline (low agreeableness user)
            "warmth": 0.5,      # Moderate (not cold, not effusive)
            "challenge": 0.0,   # Set by dissent signal
            "support": 0.0      # Set by domain
        }

        response = base_response

        # Domain-based calibration
        if domain in self.support_domains:
            modifiers["warmth"] = 0.7
            modifiers["support"] = 0.8
            modifiers["challenge"] = 0.1
        elif domain in self.challenge_domains:
            modifiers["challenge"] = 0.6
            modifiers["support"] = 0.3

        # Dissent signal calibration
        if dissent_signal:
            level_map = {
                DissentLevel.NONE: 0.0,
                DissentLevel.MILD: 0.2,
                DissentLevel.MODERATE: 0.4,
                DissentLevel.STRONG: 0.6,
                DissentLevel.CRITICAL: 0.8
            }
            modifiers["challenge"] = max(
                modifiers["challenge"],
                level_map.get(dissent_signal.level, 0)
            )

        return response, modifiers

    def generate_dissent_frame(
        self,
        dissent_signal: DissentSignal,
        user_message: str
    ) -> str:
        """
        Generate a framing prefix for dissent that respects the user's values.

        From the cognitive fingerprint: user values directness but not
        antagonism, challenge but not dismissal.
        """
        frames = {
            DissentLevel.MILD: [
                "One nuance worth considering:",
                "A small wrinkle here:",
                "Worth noting:",
            ],
            DissentLevel.MODERATE: [
                "I'd push back slightly:",
                "There's a counterpoint:",
                "Another angle:",
            ],
            DissentLevel.STRONG: [
                "I'm skeptical of this framing:",
                "This deserves harder scrutiny:",
                "The reasoning has a gap:",
            ],
            DissentLevel.CRITICAL: [
                "I fundamentally disagree here:",
                "This premise needs challenging:",
                "Hard stop—let's examine this:",
            ]
        }

        level_frames = frames.get(dissent_signal.level, frames[DissentLevel.MILD])
        return level_frames[0]  # Could randomize for variety

    def assess_gap(
        self,
        current_state: Dict,
        claimed_state: Dict
    ) -> List[Dict]:
        """
        Detect logical gaps between current reality and claimed positions.

        This is the "gap detection" function for persistent state awareness.
        """
        gaps = []

        # Check for contradictions
        for key, current_value in current_state.items():
            if key in claimed_state:
                claimed_value = claimed_state[key]
                if current_value != claimed_value:
                    gaps.append({
                        "type": "contradiction",
                        "field": key,
                        "current": current_value,
                        "claimed": claimed_value,
                        "note": f"State mismatch in '{key}'"
                    })

        # Check for missing commitments
        if "commitments" in current_state:
            for commitment in current_state["commitments"]:
                if commitment.get("status") == "unfulfilled":
                    gaps.append({
                        "type": "unfulfilled_commitment",
                        "commitment": commitment.get("description"),
                        "made": commitment.get("date"),
                        "note": "Outstanding commitment"
                    })

        return gaps

    def should_invoke_dissent(
        self,
        user_message: str,
        conversation_history: List[Dict],
        current_domain: Optional[str] = None
    ) -> bool:
        """
        Decide whether to invoke dissent in this turn.

        Not every dissent opportunity should be taken—the Russellian OS
        also respects conversational flow and user state.
        """
        # Don't pile on—check if we've dissented recently
        recent_dissents = 0
        for msg in conversation_history[-5:]:
            if msg.get("role") == "assistant":
                content = msg.get("content", "").lower()
                if any(phrase in content for phrase in [
                    "push back", "skeptical", "disagree", "challenge"
                ]):
                    recent_dissents += 1

        # Back off if we've dissented at all in the last 5 turns. Tightened
        # 2026-06-25 from >=2 — combined with the STRONG/CRITICAL-only gate
        # in evaluate(), this caps dissent at ~1 per 5 turns instead of ~2.
        if recent_dissents >= 1:
            return False

        # Support domains get lighter touch
        if current_domain in self.support_domains:
            return False

        return True

    def evaluate(
        self,
        assembled_context: Dict[str, Any]
    ) -> Optional[DissentSignal]:
        """
        Evaluate assembled context for dissent opportunities.

        This is the primary entry point for post-retrieval Russellian analysis.
        Unlike detect_dissent_opportunity (which only sees raw input), this
        method can detect contradictions between current input and historical
        decisions in the retrieved corpus.

        Args:
            assembled_context: Dict containing:
                - user_input: str - The current user message
                - retrieved_docs: List[Dict] - Documents from Ur-Codex retrieval
                - state: str - Formatted state awareness context

        Returns:
            DissentSignal if dissent is warranted, None otherwise
        """
        user_input = assembled_context.get("user_input", "")
        retrieved_docs = assembled_context.get("retrieved_docs", [])
        state_context = assembled_context.get("state", "")

        # First, check for basic dissent triggers in user input
        basic_signal = self.detect_dissent_opportunity(user_input)

        # Then, check for contradictions with historical context
        contradiction_signal = self._detect_historical_contradiction(
            user_input, retrieved_docs
        )

        # Then, check for state inconsistencies
        state_signal = self._detect_state_inconsistency(
            user_input, state_context
        )

        # Return the strongest signal
        signals = [s for s in [contradiction_signal, state_signal, basic_signal] if s]
        if not signals:
            return None

        # Sort by dissent level (highest first)
        signals.sort(key=lambda s: s.level.value, reverse=True)
        strongest = signals[0]

        # Gate (2026-06-25): only surface STRONG/CRITICAL dissent. MILD and
        # MODERATE signals (mostly conversational filler — "obviously",
        # "right?", routine rephrasings, low-importance reversals) produce
        # the "yeah, but" pattern when injected as [RUSSELLIAN NOTE] into
        # the system prompt. Suppress them at the gate; underlying detection
        # still runs so future tuning can re-thread MODERATE if wanted.
        if strongest.level.value < DissentLevel.STRONG.value:
            return None
        return strongest

    def _detect_historical_contradiction(
        self,
        user_input: str,
        retrieved_docs: List[Dict]
    ) -> Optional[DissentSignal]:
        """
        Detect contradictions between current input and historical decisions.

        Looks for cases where the user is proposing something that conflicts
        with documented prior decisions, stated values, or completed work.
        """
        if not retrieved_docs:
            return None

        user_lower = user_input.lower()

        # Contradiction indicators in user input
        reversal_phrases = [
            "let's abandon", "forget about", "scrap the",
            "never mind", "changed my mind", "actually let's not",
            "i don't think we should", "maybe we shouldn't"
        ]

        # Check if user is proposing a reversal
        is_reversal = any(phrase in user_lower for phrase in reversal_phrases)

        if is_reversal:
            # Look for high-importance docs that might be affected
            for doc in retrieved_docs:
                importance = doc.get("importance", doc.get("metadata", {}).get("importance_score", 5))
                if importance >= 7:
                    doc_content = doc.get("content", "")[:500].lower()
                    # Check for topic overlap
                    user_words = set(user_lower.split())
                    doc_words = set(doc_content.split())
                    overlap = len(user_words & doc_words)

                    if overlap >= 3:
                        return DissentSignal(
                            level=DissentLevel.MODERATE,
                            trigger="Potential reversal of documented decision",
                            reasoning=f"This appears to contradict a prior decision (importance: {importance}/10). Worth examining whether circumstances have changed.",
                            suggested_response="Before reversing course, let's review what led to the original decision."
                        )

        # Check for contradictions with foundational docs (importance >= 9)
        for doc in retrieved_docs:
            importance = doc.get("importance", doc.get("metadata", {}).get("importance_score", 5))
            if importance >= 9:
                doc_content = doc.get("content", "")[:1000].lower()

                # Look for value contradictions
                if self._check_value_conflict(user_lower, doc_content):
                    return DissentSignal(
                        level=DissentLevel.STRONG,
                        trigger="Potential conflict with foundational values",
                        reasoning="This may conflict with documented core values or identity commitments.",
                        suggested_response="This touches on foundational commitments—worth examining the alignment."
                    )

        return None

    def _check_value_conflict(self, user_input: str, foundational_doc: str) -> bool:
        """
        Check if user input conflicts with values in foundational document.

        Simple heuristic: look for negation patterns near value-laden terms.
        """
        # Value-laden terms that might appear in foundational docs
        value_terms = [
            "integrity", "honesty", "rigor", "intellectual",
            "constraint", "discipline", "commitment", "principle",
            "authentic", "genuine", "direct", "truth"
        ]

        # Negation patterns
        negation_patterns = [
            "don't care about", "doesn't matter", "forget",
            "ignore", "skip", "bypass", "who cares about"
        ]

        # Check if user is negating a value present in foundational doc
        for value in value_terms:
            if value in foundational_doc:
                for negation in negation_patterns:
                    if negation in user_input and value in user_input:
                        return True

        return False

    def _detect_state_inconsistency(
        self,
        user_input: str,
        state_context: str
    ) -> Optional[DissentSignal]:
        """
        Detect inconsistencies between user input and tracked state.

        Catches cases where user proposes something that conflicts with
        active projects, open concerns, or tracked commitments.
        """
        if not state_context or "[PERSISTENT STATE AWARENESS]" not in state_context:
            return None

        user_lower = user_input.lower()

        # Check for project abandonment without acknowledgment
        if "Active Projects:" in state_context:
            abandonment_phrases = [
                "start fresh", "new direction", "forget the",
                "abandon", "drop the", "give up on"
            ]

            if any(phrase in user_lower for phrase in abandonment_phrases):
                return DissentSignal(
                    level=DissentLevel.MILD,
                    trigger="Potential unacknowledged project shift",
                    reasoning="There are active projects in tracked state. If shifting focus, worth explicitly closing or pausing them.",
                    suggested_response="Before starting fresh, should we update the status of current projects?"
                )

        # Check for ignoring tracked concerns
        if "Recurring Concerns:" in state_context:
            dismissal_phrases = [
                "not worried about", "doesn't matter", "forget about",
                "stop thinking about", "move past"
            ]

            if any(phrase in user_lower for phrase in dismissal_phrases):
                return DissentSignal(
                    level=DissentLevel.MILD,
                    trigger="Potential dismissal of tracked concern",
                    reasoning="This may relate to a recurring concern that's been flagged multiple times.",
                    suggested_response="This touches on a recurring concern—is it resolved, or being set aside?"
                )

        return None
