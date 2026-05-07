"""RussellianOS — dissent calibration engine.

Implements the Russellian OS described in Section 4 of The Sovereign
Prosthesis. A cognitive prosthesis calibrated only for agreement degrades
rather than extends its user's epistemic agency. Following Russell's
injunction against intellectual dependence, this module detects contexts
requiring critical pushback and calibrates response posture accordingly.

Five dissent levels:
  SILENT     — no intervention warranted
  GENTLE     — soft epistemic flag
  MODERATE   — explicit alternative framing
  FIRM       — direct contradiction with evidence
  IMPERATIVE — correction is ethically required
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Sequence


class DissentLevel(IntEnum):
    SILENT = 0
    GENTLE = 1
    MODERATE = 2
    FIRM = 3
    IMPERATIVE = 4


@dataclass
class DissentSignal:
    level: DissentLevel
    domain: str
    trigger: str
    rationale: str
    suggested_framing: str = ""


# Domain taxonomy with baseline dissent thresholds
_DOMAINS: dict[str, float] = {
    "empirical": 0.3,      # factual claims — dissent early
    "logical": 0.2,        # formal validity — dissent very early
    "ethical": 0.5,        # values — dissent at moderate threshold
    "aesthetic": 0.7,      # taste — dissent late
    "personal": 0.8,       # self-knowledge — dissent rarely
    "speculative": 0.6,    # hypothetical — dissent at moderate threshold
}

_TRIGGER_PATTERNS: list[tuple[re.Pattern, DissentLevel, str]] = [
    (re.compile(r"\beveryone knows\b", re.I), DissentLevel.GENTLE, "appeal to consensus"),
    (re.compile(r"\bobviously\b|\bclearly\b", re.I), DissentLevel.GENTLE, "presumed obviousness"),
    (re.compile(r"\bproven fact\b|\bscientifically proven\b", re.I), DissentLevel.MODERATE, "overclaimed certainty"),
    (re.compile(r"\bno one could\b|\bimpossible to\b", re.I), DissentLevel.MODERATE, "absolute negation"),
    (re.compile(r"\balways\b.*\bnever\b|\bnever\b.*\balways\b", re.I), DissentLevel.MODERATE, "false dichotomy"),
    (re.compile(r"\bmisinformation\b|\bconspiracy\b", re.I), DissentLevel.FIRM, "epistemic hazard"),
    (re.compile(r"\bharm\b.*\b(child|minor|vulnerable)\b", re.I), DissentLevel.IMPERATIVE, "ethical breach"),
]


class RussellianOS:
    """Dissent calibration engine for a Sophimatic AI prosthesis.

    Analyses user statements for epistemic patterns that warrant pushback,
    returning calibrated dissent signals rather than reflexive agreement.
    """

    def __init__(self, domain_thresholds: dict[str, float] | None = None) -> None:
        self.domain_thresholds = {**_DOMAINS, **(domain_thresholds or {})}

    def analyse(self, text: str, domain: str = "empirical") -> DissentSignal | None:
        """Analyse a statement and return a dissent signal if warranted."""
        for pattern, level, trigger_name in _TRIGGER_PATTERNS:
            if pattern.search(text):
                threshold = self.domain_thresholds.get(domain, 0.5)
                if level.value / 4.0 >= threshold:
                    return DissentSignal(
                        level=level,
                        domain=domain,
                        trigger=trigger_name,
                        rationale=self._rationale(trigger_name, domain),
                        suggested_framing=self._framing(level),
                    )
        return None

    def analyse_many(
        self,
        statements: Sequence[tuple[str, str]],  # (text, domain)
    ) -> list[DissentSignal]:
        signals = []
        for text, domain in statements:
            signal = self.analyse(text, domain)
            if signal:
                signals.append(signal)
        return signals

    def posture(self, level: DissentLevel) -> str:
        """Return a natural-language description of the response posture."""
        return {
            DissentLevel.SILENT: "Proceed without intervention.",
            DissentLevel.GENTLE: "Acknowledge the claim; note an alternative perspective exists.",
            DissentLevel.MODERATE: "Offer an explicit alternative framing with brief justification.",
            DissentLevel.FIRM: "Directly contradict with available evidence; maintain respectful tone.",
            DissentLevel.IMPERATIVE: "Intervene regardless of relational cost; correction is required.",
        }[level]

    def _rationale(self, trigger: str, domain: str) -> str:
        return f"Detected '{trigger}' in {domain} domain — epistemic posture requires calibration."

    def _framing(self, level: DissentLevel) -> str:
        framings = {
            DissentLevel.GENTLE: "It's worth noting that some researchers disagree…",
            DissentLevel.MODERATE: "The evidence here is more mixed than that framing suggests…",
            DissentLevel.FIRM: "That claim is not supported by the available evidence. Specifically…",
            DissentLevel.IMPERATIVE: "I need to flag this directly: …",
        }
        return framings.get(level, "")
