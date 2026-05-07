"""
Sophimatics: The Operating Philosophy for Cognitive Extension

This module implements the Sophimatic framework from "The Sovereign Prosthesis"
for two-dimensional temporal weighting of RAG memory retrieval.

Core Principles:
1. Two-Dimensional Temporality: Chronological time vs. experiential significance
2. Russellian Operating System: Weighted toward intelligent dissent
3. Persistent State-Awareness: Track projects, logical vacancies, ongoing threads
4. Ur-Codex Governance: Longitudinal conversational history as world-historical context
5. Provenance Marking: Memory vs. inference vs. speculation
"""

from .temporal_weighting import TemporalWeightingEngine
from .ur_codex import UrCodexManager
from .russellian_os import RussellianOS
from .provenance import ProvenanceTracker
from .state_awareness import StateAwarenessEngine

__all__ = [
    'TemporalWeightingEngine',
    'UrCodexManager',
    'RussellianOS',
    'ProvenanceTracker',
    'StateAwarenessEngine'
]
