"""Sophimatics — reference implementation for The Sovereign Prosthesis (IACAP 2026)."""

from .ur_codex import UrCodexManager
from .temporal_weighting import TemporalWeightingEngine, TemporalScore
from .russellian_os import RussellianOS, DissentLevel
from .state_awareness import StateAwarenessEngine
from .wiki_integration import WikiSophimaticsEngine

__all__ = [
    "UrCodexManager",
    "TemporalWeightingEngine",
    "TemporalScore",
    "RussellianOS",
    "DissentLevel",
    "StateAwarenessEngine",
    "WikiSophimaticsEngine",
]

__version__ = "0.1.0"
__author__ = "Michael Bouchard, Pauper King LLC"
__license__ = "CC BY 4.0"
