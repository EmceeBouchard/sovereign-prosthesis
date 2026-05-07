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

from typing import Dict, List, Optional, Tuple
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
        # Dissent triggers based on cognitive fingerprint
        self.dissent_triggers = {
            # Overconfidence patterns
            "absolutist_language": [
                "always", "never", "definitely", "certainly",
                "obviously", "clearly", "undoubtedly", "must be"
            ],

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
            ],

            # Confirmation seeking
            "validation_seeking": [
                "right?", "don't you think?", "wouldn't you agree?",
                "you see what I mean?", "makes sense, right?"
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

        # Check for absolutist language
        for trigger_word in self.dissent_triggers["absolutist_language"]:
            if trigger_word in message_lower:
                return DissentSignal(
                    level=DissentLevel.MILD,
                    trigger=f"Absolutist language: '{trigger_word}'",
                    reasoning="Absolute claims often have exceptions worth examining",
                    suggested_response=f"Consider framing: 'In most cases...' or 'Typically...' rather than '{trigger_word}'"
                )

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

        # Check for validation seeking (user explicitly doesn't want yes-men)
        for phrase in self.dissent_triggers["validation_seeking"]:
            if phrase in message_lower:
                return DissentSignal(
                    level=DissentLevel.MILD,
                    trigger=f"Validation seeking: '{phrase}'",
                    reasoning="User values genuine assessment over agreement",
                    suggested_response="Rather than confirming, offer actual analysis"
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

        # Back off if we've been challenging frequently
        if recent_dissents >= 2:
            return False

        # Support domains get lighter touch
        if current_domain in self.support_domains:
            return False

        return True
