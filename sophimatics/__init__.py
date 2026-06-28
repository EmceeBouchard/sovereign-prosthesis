"""
Sophimatics: The Operating Philosophy for Cognitive Extension

This module implements the Sophimatic framework from "The Sovereign Prosthesis"
for three-dimensional temporal weighting of RAG memory retrieval.

Core Principles:
1. Three-Dimensional Temporality: α experiential, β chronological, γ citation velocity
2. Unified Memory Architecture: Four tiers with SMS-driven promotion/deprecation
3. Russellian Operating System: Weighted toward intelligent dissent
4. Persistent State-Awareness: Track projects, logical vacancies, ongoing threads
5. Ur-Codex Governance: Longitudinal conversational history as world-historical context
6. Provenance Marking: Memory vs. inference vs. speculation
7. Corpus Authoring Protocol: Clara can draft corpus documents for Michael's approval
"""

from .temporal_weighting import TemporalWeightingEngine
from .ur_codex import UrCodexManager
from .russellian_os import RussellianOS
from .provenance import ProvenanceTracker
from .state_awareness import StateAwarenessEngine
from .wiki_integration import WikiSophimaticsEngine, WikiPageMeta, create_wiki_engine
from .memory_scoring import (
    SessionType,
    MemoryTier,
    SMSBreakdown,
    classify_session,
    calculate_sms,
)
from .memory_tiers import (
    assign_tier,
    promote,
    demote,
    pin,
    get_tier_status,
    get_pending_drafts,
    queue_corpus_draft,
    approve_corpus_draft,
    discard_corpus_draft,
    log_retrieval,
    gamma_adjustment,
    build_pruning_digest,
)
from .session_logger import log_exchange, read_day_log
from .memory_manager import read_memory, get_memory_stats, add_entries as add_memory_entries
from .nightly_loop import SophimaticsNightlyLoop, run_nightly_consolidation

__all__ = [
    'TemporalWeightingEngine',
    'UrCodexManager',
    'RussellianOS',
    'ProvenanceTracker',
    'StateAwarenessEngine',
    'WikiSophimaticsEngine',
    'WikiPageMeta',
    'create_wiki_engine',
    # Memory architecture
    'SessionType',
    'MemoryTier',
    'SMSBreakdown',
    'classify_session',
    'calculate_sms',
    'assign_tier',
    'promote',
    'demote',
    'pin',
    'get_tier_status',
    'get_pending_drafts',
    'queue_corpus_draft',
    'approve_corpus_draft',
    'discard_corpus_draft',
    'log_retrieval',
    'gamma_adjustment',
    'build_pruning_digest',
    # Sophimatics Loop
    'log_exchange',
    'read_day_log',
    'read_memory',
    'get_memory_stats',
    'add_memory_entries',
    'SophimaticsNightlyLoop',
    'run_nightly_consolidation',
]
