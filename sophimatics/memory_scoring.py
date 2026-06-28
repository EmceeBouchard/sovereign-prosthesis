"""
Sophimatics Memory Score (SMS) — Four-Dimension Scoring System

Implements the unified scoring criteria from the Sophimatics Unified Memory
Architecture specification. Every session or document receives a score from
0.0 to 1.0 that determines tier placement and promotion/demotion direction.

Four dimensions:
  1. Output Type          (weight: 0.30)
  2. Novel Position Staking (weight: 0.25)
  3. Cross-Corpus Resonance (weight: 0.25)
  4. Explicit Markers     (weight: 0.20)

Score ceiling is set by Session Character Classification before dimension
scoring begins.
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SessionType(str, Enum):
    GENERATIVE    = "GENERATIVE"     # Producing: writing, deciding, building
    SYNTHETIC     = "SYNTHETIC"      # Ingesting external material + synthesizing
    ANALYTICAL    = "ANALYTICAL"     # Working through a problem toward conclusion
    RESEARCH      = "RESEARCH"       # Gathering info, ducks in a row
    EXPLORATORY   = "EXPLORATORY"    # Daydreaming, hypotheticals
    ADMINISTRATIVE = "ADMINISTRATIVE" # Logistics, scheduling, budgeting
    TRANSACTIONAL = "TRANSACTIONAL"  # Quick Q&A, lookup, no synthesis


class MemoryTier(str, Enum):
    PERMANENT_CORPUS = "PERMANENT_CORPUS"
    WORKING_MEMORY   = "WORKING_MEMORY"
    EPHEMERAL_BUFFER = "EPHEMERAL_BUFFER"
    PRUNED           = "PRUNED"


# ---------------------------------------------------------------------------
# Session ceiling map
# ---------------------------------------------------------------------------

SESSION_CEILING: dict[SessionType, float] = {
    SessionType.GENERATIVE:     1.0,
    SessionType.SYNTHETIC:      0.85,
    SessionType.ANALYTICAL:     0.70,
    SessionType.RESEARCH:       0.45,
    SessionType.EXPLORATORY:    0.30,
    SessionType.ADMINISTRATIVE: 0.15,
    SessionType.TRANSACTIONAL:  0.05,
}

# Session types that can trigger corpus authoring (Part IX)
AUTHORING_ELIGIBLE_SESSIONS = {
    SessionType.GENERATIVE,
    SessionType.SYNTHETIC,
    SessionType.ANALYTICAL,
}

# Session types that receive a recency bonus on alpha (chronological) axis
RECENCY_ELIGIBLE_SESSIONS = {
    SessionType.GENERATIVE,
    SessionType.SYNTHETIC,
}


# ---------------------------------------------------------------------------
# Score data
# ---------------------------------------------------------------------------

@dataclass
class SMSBreakdown:
    """Full breakdown of a Sophimatics Memory Score calculation."""
    session_type: SessionType
    session_ceiling: float

    # Raw dimension scores (0.0 – 1.0 each)
    output_type_score: float        = 0.0   # weight 0.30
    novel_position_score: float     = 0.0   # weight 0.25
    cross_corpus_score: float       = 0.0   # weight 0.25
    explicit_markers_score: float   = 0.0   # weight 0.20

    # Signals detected
    promotion_signals: List[str] = field(default_factory=list)
    deprecation_signals: List[str] = field(default_factory=list)

    # Final score (after ceiling applied)
    raw_sms: float  = 0.0   # before ceiling
    final_sms: float = 0.0  # after ceiling

    @property
    def tier(self) -> MemoryTier:
        if self.final_sms >= 0.75:
            return MemoryTier.PERMANENT_CORPUS
        elif self.final_sms >= 0.50:
            return MemoryTier.WORKING_MEMORY
        elif self.final_sms >= 0.25:
            return MemoryTier.EPHEMERAL_BUFFER
        else:
            return MemoryTier.PRUNED

    @property
    def ttl_days(self) -> Optional[int]:
        """TTL in days. None means no automatic expiry."""
        if self.tier == MemoryTier.PERMANENT_CORPUS:
            return None
        elif self.tier == MemoryTier.WORKING_MEMORY:
            return 30
        elif self.tier == MemoryTier.EPHEMERAL_BUFFER:
            return 30
        else:
            return 7  # grace period before pruning


# ---------------------------------------------------------------------------
# Session character classifier
# ---------------------------------------------------------------------------

# Query patterns that suggest each session type (checked on first 3 exchanges)
_GENERATIVE_SIGNALS = [
    r"\b(write|draft|compose|create|build|implement|design|make|produce|generate)\b",
    r"\b(let'?s? (write|draft|build|create|make))\b",
    r"\b(final (call|decision|version))\b",
    r"\b(this is the (architecture|spec|design))\b",
    r"transfer packet",
    r"\bv\d+\.\d+\b",  # versioning language
]

_SYNTHETIC_SIGNALS = [
    r"\b(summarize|synthesize|integrate|combine|distill)\b",
    r"\b(read this|process this|here'?s? (a|an|the) (paper|article|doc))\b",
    r"\b(what do you make of|what'?s? your (take|read) on)\b",
]

_ANALYTICAL_SIGNALS = [
    r"\b(analyze|analyse|work through|think through|figure out|diagnose)\b",
    r"\b(what'?s? (wrong|broken|the problem|the issue))\b",
    r"\b(how (do|should) (we|i))\b",
    r"\b(why (is|does|did|would))\b",
]

_RESEARCH_SIGNALS = [
    r"\b(search for|look up|find out|research|investigate)\b",
    r"\b(what (is|are|does|do))\b",
    r"\b(tell me (about|how))\b",
    r"\bjust (curious|wondering)\b",
    r"\bquick question\b",
]

_EXPLORATORY_SIGNALS = [
    r"\b(just thinking|daydream|hypothetically|what if|imagine if|blue.?sky)\b",
    r"\b(thinking out loud|brainstorm)\b",
    r"\b(what would happen if|suppose|let'?s? say)\b",
]

_ADMINISTRATIVE_SIGNALS = [
    r"\b(schedule|budget|logistics|invoice|calendar|meeting|appointment)\b",
    r"\b(how much (does|would)|cost|price|estimate)\b",
    r"\b(remind me to|add to (my )?list|todo)\b",
]

_TRANSACTIONAL_SIGNALS = [
    r"\b(what (time|day|date|year) (is|was))\b",
    r"\b(define|definition of|meaning of)\b",
    r"\b(convert|translate|calculate)\b",
    r"\b(yes|no|sure|okay|thanks)\b",
]

_TYPE_PATTERNS = [
    (SessionType.GENERATIVE,     _GENERATIVE_SIGNALS),
    (SessionType.SYNTHETIC,      _SYNTHETIC_SIGNALS),
    (SessionType.ANALYTICAL,     _ANALYTICAL_SIGNALS),
    (SessionType.EXPLORATORY,    _EXPLORATORY_SIGNALS),
    (SessionType.ADMINISTRATIVE, _ADMINISTRATIVE_SIGNALS),
    (SessionType.TRANSACTIONAL,  _TRANSACTIONAL_SIGNALS),
    (SessionType.RESEARCH,       _RESEARCH_SIGNALS),  # fallback
]


def classify_session(messages: List[str]) -> SessionType:
    """
    Infer session type from the first three (or all) user messages.

    Scans each message against pattern lists and returns the type with
    the most signal matches. Falls back to RESEARCH if nothing fires.
    """
    probe = " ".join(m.lower() for m in messages[:3])
    scores: dict[SessionType, int] = {t: 0 for t, _ in _TYPE_PATTERNS}

    for session_type, patterns in _TYPE_PATTERNS:
        for pat in patterns:
            if re.search(pat, probe):
                scores[session_type] += 1

    best = max(scores, key=lambda t: scores[t])
    return best if scores[best] > 0 else SessionType.RESEARCH


# ---------------------------------------------------------------------------
# Explicit marker detection
# ---------------------------------------------------------------------------

_PROMOTION_PATTERNS = [
    (r"\bpin that\b",                 "pin that"),
    (r"\blog this\b",                 "log this"),
    (r"\bthat'?s? decided\b",         "that's decided"),
    (r"\badd (this )?to (the )?corpus\b", "add to corpus"),
    (r"\bremember this\b",            "remember this"),
    (r"\bthis is the architecture\b", "this is the architecture"),
    (r"\bfinal call\b",               "final call"),
    (r"\btransfer packet\b",          "transfer packet"),
    (r"\bv\d+\.\d+\b",               "versioning"),
    (r"\bsupersedes\b",               "supersedes"),
]

_DEPRECATION_PATTERNS = [
    (r"\bjust thinking out loud\b",   "just thinking out loud"),
    (r"\bthinking out loud\b",        "thinking out loud"),
    (r"\bdaydream(ing)?\b",           "daydreaming"),
    (r"\bhypothetically\b",           "hypothetically"),
    (r"\bwhat if\b",                  "what if (no resolution)"),
    (r"\bignore that\b",              "ignore that"),
    (r"\bscratch that\b",             "scratch that"),
    (r"\bjust curious\b",             "just curious"),
    (r"\bquick question\b",           "quick question"),
]


def detect_explicit_markers(text: str) -> Tuple[List[str], List[str]]:
    """
    Scan text for promotion and deprecation signal phrases.

    Returns (promotion_signals, deprecation_signals).
    """
    lowered = text.lower()
    promotions = [label for pat, label in _PROMOTION_PATTERNS if re.search(pat, lowered)]
    deprecations = [label for pat, label in _DEPRECATION_PATTERNS if re.search(pat, lowered)]
    return promotions, deprecations


def score_explicit_markers(
    promotion_signals: List[str],
    deprecation_signals: List[str],
) -> float:
    """
    Convert detected signals into a 0.0–1.0 score.

    Net score = promotion weight - deprecation weight, clamped to [0,1].
    Neutral (no signals) returns 0.5.
    """
    if not promotion_signals and not deprecation_signals:
        return 0.5  # neutral

    promo_weight = min(1.0, len(promotion_signals) * 0.3)
    depr_weight  = min(1.0, len(deprecation_signals) * 0.3)

    raw = 0.5 + (promo_weight * 0.5) - (depr_weight * 0.5)
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# Output type scoring
# ---------------------------------------------------------------------------

_OUTPUT_TYPE_TABLE = [
    # (score, patterns)
    (1.0, [r"\b(creative work|play|poem|essay|screenplay|novel|script)\b"]),
    (1.0, [r"\b(committed|final) (architecture|decision|call)\b",
           r"\bthis is the architecture\b"]),
    (0.9, [r"\bphilosophical (position|stance|argument)\b"]),
    (0.9, [r"\b(academic|publishable|paper|journal|manuscript)\b"]),
    (0.8, [r"\b(specification|build plan|spec|blueprint)\b"]),
    (0.7, [r"\b(resolved|resolution) (decision|question)\b",
           r"\bnext (steps|actions)\b"]),
    (0.6, [r"\b(research synthesis|synthesis|concluded|conclusions)\b"]),
    (0.3, [r"\b(research intake|notes|intake)\b"]),
    (0.2, [r"\b(exploratory|daydream|brainstorm)\b"]),
    (0.1, [r"\b(logistic|admin|scheduling|invoice)\b"]),
    (0.0, [r"\b(quick question|web search|google|look up)\b"]),
]


def score_output_type(text: str) -> float:
    """
    Infer output type score from session content.

    Returns the score of the first matching pattern, defaulting to 0.3
    (research intake) if nothing fires.
    """
    lowered = text.lower()
    for score, patterns in _OUTPUT_TYPE_TABLE:
        for pat in patterns:
            if re.search(pat, lowered):
                return score
    return 0.3  # default: research intake without conclusions


# ---------------------------------------------------------------------------
# Novel position staking
# ---------------------------------------------------------------------------

_POSITION_SIGNALS = [
    (1.0, [r"\bi (believe|hold|argue|maintain|claim|assert)\b",
           r"\bmy position (is|on)\b",
           r"\bphilosophical position\b"]),
    (0.8, [r"\b(refined|sharpened|updated) (my|this|the) (view|position|stance)\b",
           r"\bnew (project|direction|commitment)\b"]),
    (0.8, [r"\bcommitted to\b", r"\bwe'?re? (going with|doing)\b"]),
    (0.6, [r"\bi (prefer|like|want|choose)\b",
           r"\bmy (preference|aesthetic)\b"]),
    (0.4, [r"\bi (think|feel|suspect|wonder)\b",
           r"\bmy (opinion|take) (is|on)\b"]),
    (0.2, [r"\binteresting\b", r"\bnot sure\b", r"\bmaybe\b"]),
]


def score_novel_position(text: str) -> float:
    """
    Estimate how strongly a new position was staked.

    Returns the highest matching score, defaulting to 0.0.
    """
    lowered = text.lower()
    for score, patterns in _POSITION_SIGNALS:
        for pat in patterns:
            if re.search(pat, lowered):
                return score
    return 0.0


# ---------------------------------------------------------------------------
# Cross-corpus resonance
# ---------------------------------------------------------------------------

# Known permanent corpus themes for lightweight keyword matching.
# Phase 2 will replace this with embedding comparison.
CORPUS_THEMES = [
    # Core philosophy
    "sovereign prosthesis", "sophimatics", "ur-codex", "ur codex",
    "cognitive prosthesis", "cognitive extension", "world-historical context",
    # Active projects
    "clara", "pauper king", "showbusiness",
    # Philosophical positions
    "russellian", "dissent calibration", "epistemic",
    # Creative works
    "what i believe", "solarpunk",
]


def score_cross_corpus_resonance(text: str) -> float:
    """
    Lightweight keyword-match against known corpus themes.

    Phase 2 will use embedding cosine similarity.
    Returns 0.0–1.0 based on number of distinct themes hit.
    """
    lowered = text.lower()
    hits = sum(1 for theme in CORPUS_THEMES if theme in lowered)

    if hits >= 3:
        return 1.0
    elif hits == 2:
        return 0.8
    elif hits == 1:
        return 0.6
    else:
        return 0.0


# ---------------------------------------------------------------------------
# Main SMS calculator
# ---------------------------------------------------------------------------

DIMENSION_WEIGHTS = {
    "output_type":      0.30,
    "novel_position":   0.25,
    "cross_corpus":     0.25,
    "explicit_markers": 0.20,
}


def calculate_sms(
    session_type: SessionType,
    full_text: str,
    corpus_resonance_override: Optional[float] = None,
) -> SMSBreakdown:
    """
    Calculate the Sophimatics Memory Score for a session or document.

    Args:
        session_type: Pre-classified session character.
        full_text: Combined text of all session messages / document content.
        corpus_resonance_override: If provided, skip keyword matching and use
            this value directly (for Phase 2 embedding-based scoring).

    Returns:
        SMSBreakdown with raw score, ceiling-applied final score, and tier.
    """
    ceiling = SESSION_CEILING[session_type]

    # Dimension 1: Output type
    d1 = score_output_type(full_text)

    # Dimension 2: Novel position staking
    d2 = score_novel_position(full_text)

    # Dimension 3: Cross-corpus resonance
    d3 = (
        corpus_resonance_override
        if corpus_resonance_override is not None
        else score_cross_corpus_resonance(full_text)
    )

    # Dimension 4: Explicit markers
    promo, depr = detect_explicit_markers(full_text)
    d4 = score_explicit_markers(promo, depr)

    # Weighted average
    raw = (
        d1 * DIMENSION_WEIGHTS["output_type"]
        + d2 * DIMENSION_WEIGHTS["novel_position"]
        + d3 * DIMENSION_WEIGHTS["cross_corpus"]
        + d4 * DIMENSION_WEIGHTS["explicit_markers"]
    )

    # Apply session ceiling
    final = min(raw, ceiling)

    return SMSBreakdown(
        session_type=session_type,
        session_ceiling=ceiling,
        output_type_score=d1,
        novel_position_score=d2,
        cross_corpus_score=d3,
        explicit_markers_score=d4,
        promotion_signals=promo,
        deprecation_signals=depr,
        raw_sms=raw,
        final_sms=final,
    )
