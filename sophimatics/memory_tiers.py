"""
Memory Tier Manager — Sophimatics Unified Memory Architecture

Manages the four-tier memory hierarchy:
  PERMANENT_CORPUS → WORKING_MEMORY → EPHEMERAL_BUFFER → PRUNED

Responsibilities:
- Tier assignment and TTL enforcement
- Promotion and demotion pathways
- Pruning queue with 7-day grace period
- Corpus draft queue (Clara-authored documents, max 3)
- Retrieval logging (citation quality / Gamma axis)
- Weekly pruning digest
- Memory audit log (permanent, survives pruning)

All state is persisted as JSON under backend/data/memory/.
"""

import json
import uuid
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sophimatics.memory_scoring import (
    MemoryTier,
    SMSBreakdown,
    SessionType,
    calculate_sms,
    classify_session,
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BASE_DIR = Path(__file__).parent.parent / "data" / "memory"
_BASE_DIR.mkdir(parents=True, exist_ok=True)

TIER_ASSIGNMENTS_PATH   = _BASE_DIR / "tier_assignments.json"
RETRIEVAL_LOG_PATH      = _BASE_DIR / "retrieval_log.json"
CORPUS_DRAFTS_PATH      = _BASE_DIR / "corpus_drafts.json"
MEMORY_AUDIT_LOG_PATH   = _BASE_DIR / "memory_audit_log.json"
SESSION_SCORES_PATH     = _BASE_DIR / "session_classifications.json"

MAX_CORPUS_DRAFTS = 3

AUTHORING_ELIGIBLE_SESSIONS = {
    SessionType.GENERATIVE,
    SessionType.SYNTHETIC,
    SessionType.ANALYTICAL,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> Any:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _load_list(path: Path) -> List:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def _save(path: Path, data: Any) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Tier assignments store
# ---------------------------------------------------------------------------

def load_tier_assignments() -> Dict[str, Dict]:
    return _load(TIER_ASSIGNMENTS_PATH)


def save_tier_assignments(assignments: Dict[str, Dict]) -> None:
    _save(TIER_ASSIGNMENTS_PATH, assignments)


def assign_tier(
    doc_id: str,
    sms: float,
    session_type: SessionType,
    session_id: Optional[str] = None,
    topic_summary: str = "",
    pinned: bool = False,
) -> Dict:
    """
    Assign or update the tier for a document/session.

    Returns the assignment record.
    """
    assignments = load_tier_assignments()

    if sms >= 0.75:
        tier = MemoryTier.PERMANENT_CORPUS
        ttl_days = None
    elif sms >= 0.50:
        tier = MemoryTier.WORKING_MEMORY
        ttl_days = 30
    elif sms >= 0.25:
        tier = MemoryTier.EPHEMERAL_BUFFER
        ttl_days = 30
    else:
        tier = MemoryTier.PRUNED
        ttl_days = 7  # grace period

    now = datetime.utcnow()
    expires_at = (now + timedelta(days=ttl_days)).isoformat() if ttl_days else None

    record = {
        "doc_id": doc_id,
        "session_id": session_id,
        "tier": tier.value,
        "sms": sms,
        "session_type": session_type.value,
        "topic_summary": topic_summary,
        "assigned_at": now.isoformat(),
        "expires_at": expires_at,
        "pinned": pinned,
        "authored_by_clara": False,
        "promotion_history": assignments.get(doc_id, {}).get("promotion_history", []),
    }

    assignments[doc_id] = record
    save_tier_assignments(assignments)
    return record


def get_tier(doc_id: str) -> Optional[Dict]:
    assignments = load_tier_assignments()
    return assignments.get(doc_id)


def promote(doc_id: str, reason: str = "manual") -> Optional[Dict]:
    """Move a document up one tier."""
    assignments = load_tier_assignments()
    if doc_id not in assignments:
        return None

    rec = assignments[doc_id]
    current = MemoryTier(rec["tier"])

    tier_order = [
        MemoryTier.EPHEMERAL_BUFFER,
        MemoryTier.WORKING_MEMORY,
        MemoryTier.PERMANENT_CORPUS,
    ]

    if current == MemoryTier.PERMANENT_CORPUS:
        return rec  # already at top

    if current == MemoryTier.PRUNED:
        next_tier = MemoryTier.EPHEMERAL_BUFFER
    else:
        idx = tier_order.index(current)
        next_tier = tier_order[min(idx + 1, len(tier_order) - 1)]

    now = datetime.utcnow()
    ttl_map = {
        MemoryTier.PERMANENT_CORPUS: None,
        MemoryTier.WORKING_MEMORY: 30,
        MemoryTier.EPHEMERAL_BUFFER: 30,
    }
    ttl_days = ttl_map.get(next_tier)
    expires_at = (now + timedelta(days=ttl_days)).isoformat() if ttl_days else None

    rec["tier"] = next_tier.value
    rec["expires_at"] = expires_at
    rec["promotion_history"].append({
        "from": current.value,
        "to": next_tier.value,
        "reason": reason,
        "at": now.isoformat(),
    })
    assignments[doc_id] = rec
    save_tier_assignments(assignments)

    _audit(doc_id, "promoted", current.value, next_tier.value, reason, rec.get("sms", 0))
    return rec


def demote(doc_id: str, reason: str = "manual") -> Optional[Dict]:
    """Move a document down one tier."""
    assignments = load_tier_assignments()
    if doc_id not in assignments:
        return None

    rec = assignments[doc_id]
    if rec.get("pinned"):
        return rec  # pinned docs are immune

    current = MemoryTier(rec["tier"])

    tier_order = [
        MemoryTier.PRUNED,
        MemoryTier.EPHEMERAL_BUFFER,
        MemoryTier.WORKING_MEMORY,
        MemoryTier.PERMANENT_CORPUS,
    ]

    if current == MemoryTier.PRUNED:
        return rec

    idx = tier_order.index(current)
    next_tier = tier_order[max(idx - 1, 0)]

    now = datetime.utcnow()
    ttl_map = {
        MemoryTier.WORKING_MEMORY: 30,
        MemoryTier.EPHEMERAL_BUFFER: 30,
        MemoryTier.PRUNED: 7,
    }
    ttl_days = ttl_map.get(next_tier)
    expires_at = (now + timedelta(days=ttl_days)).isoformat() if ttl_days else None

    rec["tier"] = next_tier.value
    rec["expires_at"] = expires_at
    rec["promotion_history"].append({
        "from": current.value,
        "to": next_tier.value,
        "reason": reason,
        "at": now.isoformat(),
    })
    assignments[doc_id] = rec
    save_tier_assignments(assignments)

    _audit(doc_id, "demoted", current.value, next_tier.value, reason, rec.get("sms", 0))
    return rec


def pin(doc_id: str) -> Optional[Dict]:
    """Pin a document — permanently immune to deprecation."""
    assignments = load_tier_assignments()
    if doc_id not in assignments:
        return None
    rec = assignments[doc_id]
    rec["pinned"] = True
    rec["tier"] = MemoryTier.PERMANENT_CORPUS.value
    rec["expires_at"] = None
    assignments[doc_id] = rec
    save_tier_assignments(assignments)
    _audit(doc_id, "pinned", rec.get("tier", ""), "PERMANENT_CORPUS", "manual pin", rec.get("sms", 0))
    return rec


def prune_immediate(doc_id: str) -> Optional[Dict]:
    """Immediately move a document to PRUNED, skipping grace period."""
    assignments = load_tier_assignments()
    if doc_id not in assignments:
        return None
    rec = assignments[doc_id]
    old_tier = rec["tier"]
    rec["tier"] = MemoryTier.PRUNED.value
    rec["expires_at"] = None
    assignments[doc_id] = rec
    save_tier_assignments(assignments)
    _audit(doc_id, "pruned_immediate", old_tier, "PRUNED", "manual prune", rec.get("sms", 0))
    return rec


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def _audit(
    doc_id: str,
    action: str,
    from_tier: str,
    to_tier: str,
    reason: str,
    sms: float,
) -> None:
    log = _load_list(MEMORY_AUDIT_LOG_PATH)
    log.append({
        "doc_id": doc_id,
        "action": action,
        "from_tier": from_tier,
        "to_tier": to_tier,
        "reason": reason,
        "sms": sms,
        "timestamp": _now_iso(),
    })
    _save(MEMORY_AUDIT_LOG_PATH, log)


# ---------------------------------------------------------------------------
# TTL enforcement — called by the pruning pipeline
# ---------------------------------------------------------------------------

def enforce_ttl() -> List[str]:
    """
    Move expired documents to the pruning queue.

    Returns list of doc_ids that entered the pruning queue.
    """
    assignments = load_tier_assignments()
    now = datetime.utcnow()
    queued = []

    for doc_id, rec in assignments.items():
        if rec.get("pinned"):
            continue
        tier = MemoryTier(rec["tier"])
        if tier == MemoryTier.PRUNED:
            continue

        expires_at = rec.get("expires_at")
        if not expires_at:
            continue

        exp_dt = datetime.fromisoformat(expires_at)
        if now >= exp_dt:
            rec["tier"] = MemoryTier.PRUNED.value
            grace_expiry = (now + timedelta(days=7)).isoformat()
            rec["expires_at"] = grace_expiry
            rec["promotion_history"].append({
                "from": tier.value,
                "to": MemoryTier.PRUNED.value,
                "reason": "TTL expired",
                "at": now.isoformat(),
            })
            assignments[doc_id] = rec
            _audit(doc_id, "ttl_expired", tier.value, "PRUNED", "TTL expired", rec.get("sms", 0))
            queued.append(doc_id)

    save_tier_assignments(assignments)
    return queued


# ---------------------------------------------------------------------------
# Pruning digest — surfaces grace-period docs before final removal
# ---------------------------------------------------------------------------

def build_pruning_digest() -> Dict:
    """
    Build a digest of documents in the grace-period pruning queue.

    Documents that have been in PRUNED tier for less than 7 days
    are listed for Michael's review.
    """
    assignments = load_tier_assignments()
    now = datetime.utcnow()
    candidates = []
    permanently_remove = []

    for doc_id, rec in assignments.items():
        if MemoryTier(rec["tier"]) != MemoryTier.PRUNED:
            continue

        expires_at = rec.get("expires_at")
        if not expires_at:
            # Old-style prune with no expiry — add grace period
            rec["expires_at"] = (now + timedelta(days=7)).isoformat()
            candidates.append(rec)
            continue

        exp_dt = datetime.fromisoformat(expires_at)
        if now < exp_dt:
            candidates.append(rec)
        else:
            permanently_remove.append(doc_id)

    # Remove expired-grace documents from active index
    if permanently_remove:
        updated = load_tier_assignments()
        for doc_id in permanently_remove:
            if doc_id in updated:
                rec = updated[doc_id]
                _audit(doc_id, "permanently_removed", "PRUNED", "PRUNED",
                       "grace period expired", rec.get("sms", 0))
                del updated[doc_id]
        save_tier_assignments(updated)

    return {
        "generated_at": _now_iso(),
        "candidates_for_rescue": candidates,
        "permanently_removed": permanently_remove,
        "rescue_instruction": (
            "Run `clara memory promote <doc_id>` to rescue any document before its grace period expires."
        ),
    }


# ---------------------------------------------------------------------------
# Retrieval log (Gamma axis — citation velocity)
# ---------------------------------------------------------------------------

def log_retrieval(
    doc_id: str,
    query: str,
    query_type: str = "general",
    session_id: Optional[str] = None,
) -> None:
    """Record that a document was retrieved, for Gamma axis tracking."""
    log = _load_list(RETRIEVAL_LOG_PATH)
    log.append({
        "doc_id": doc_id,
        "query": query[:200],
        "query_type": query_type,
        "session_id": session_id,
        "timestamp": _now_iso(),
    })
    _save(RETRIEVAL_LOG_PATH, log)


def get_citation_velocity(doc_id: str, window_days: int = 30) -> int:
    """Return number of retrievals for a doc in the past window_days."""
    log = _load_list(RETRIEVAL_LOG_PATH)
    cutoff = (datetime.utcnow() - timedelta(days=window_days)).isoformat()
    return sum(
        1 for entry in log
        if entry["doc_id"] == doc_id and entry["timestamp"] >= cutoff
    )


def gamma_adjustment(doc_id: str) -> float:
    """
    Calculate Gamma axis adjustment to SMS based on citation velocity.

    Returns delta to apply to SMS: +0.1 (high velocity) or -0.1 (zero velocity).
    """
    velocity_30d = get_citation_velocity(doc_id, 30)
    velocity_90d = get_citation_velocity(doc_id, 90)

    if velocity_30d >= 10:
        return +0.1
    elif velocity_90d == 0:
        return -0.1
    return 0.0


# ---------------------------------------------------------------------------
# Session classification store
# ---------------------------------------------------------------------------

def save_session_classification(
    session_id: str,
    session_type: SessionType,
    breakdown: SMSBreakdown,
    topic_summary: str = "",
) -> None:
    scores = _load(SESSION_SCORES_PATH)
    scores[session_id] = {
        "session_id": session_id,
        "session_type": session_type.value,
        "sms_final": breakdown.final_sms,
        "sms_raw": breakdown.raw_sms,
        "tier": breakdown.tier.value,
        "output_type_score": breakdown.output_type_score,
        "novel_position_score": breakdown.novel_position_score,
        "cross_corpus_score": breakdown.cross_corpus_score,
        "explicit_markers_score": breakdown.explicit_markers_score,
        "promotion_signals": breakdown.promotion_signals,
        "deprecation_signals": breakdown.deprecation_signals,
        "topic_summary": topic_summary,
        "scored_at": _now_iso(),
    }
    _save(SESSION_SCORES_PATH, scores)


# ---------------------------------------------------------------------------
# Corpus draft queue (Part IX)
# ---------------------------------------------------------------------------

def load_corpus_drafts() -> List[Dict]:
    return _load_list(CORPUS_DRAFTS_PATH)


def save_corpus_drafts(drafts: List[Dict]) -> None:
    _save(CORPUS_DRAFTS_PATH, drafts)


def queue_corpus_draft(
    content: str,
    category: str,
    session_id: str,
    sms_score: float,
    filename_slug: str = "",
) -> Optional[Dict]:
    """
    Add a Clara-authored document to the pending review queue.

    Returns None if queue is full (MAX_CORPUS_DRAFTS = 3).
    """
    drafts = load_corpus_drafts()
    active = [d for d in drafts if d.get("status") == "pending"]

    if len(active) >= MAX_CORPUS_DRAFTS:
        return None  # Queue full — log synthesis moment but don't draft

    today = datetime.utcnow().strftime("%Y%m%d")
    slug = filename_slug or session_id[:8]
    filename = f"CLARA_AUTHORED_{category.upper()}_{today}_{slug}.md"

    draft = {
        "draft_id": str(uuid.uuid4()),
        "filename": filename,
        "category": category,
        "content": content,
        "sms_score": sms_score,
        "source_session_id": session_id,
        "authored_by": "Clara",
        "status": "pending",
        "created_at": _now_iso(),
        "approved_at": None,
        "approved_sms": None,
    }

    drafts.append(draft)
    save_corpus_drafts(drafts)
    return draft


def approve_corpus_draft(
    draft_id: str,
    revised_content: Optional[str] = None,
    packet_id: Optional[int] = None,
    packet_path: Optional[str] = None,
) -> Optional[Dict]:
    """Mark a corpus draft approved (optionally with edited content).

    Storage only — the packet itself is written through the shared corpus
    writer (dreaming.writer) by memory_approval.approve_draft, which records
    the resulting packet_id/packet_path here.
    """
    drafts = load_corpus_drafts()
    for i, d in enumerate(drafts):
        if d["draft_id"] == draft_id:
            if revised_content:
                d["content"] = revised_content
            d["status"] = "approved"
            d["approved_at"] = _now_iso()
            d["authored_by"] = "Clara"
            if packet_id is not None:
                d["packet_id"] = packet_id
            if packet_path is not None:
                d["packet_path"] = packet_path
            drafts[i] = d
            save_corpus_drafts(drafts)
            _audit(
                draft_id, "corpus_draft_approved",
                "corpus_drafts", "PERMANENT_CORPUS",
                "Michael approved", d.get("sms_score", 0),
            )
            return d
    return None


def discard_corpus_draft(draft_id: str, reason: str = "") -> Optional[Dict]:
    """Reject a corpus draft — archived in the queue file with reason, never deleted."""
    drafts = load_corpus_drafts()
    for i, d in enumerate(drafts):
        if d["draft_id"] == draft_id:
            d["status"] = "discarded"
            d["rejected_at"] = _now_iso()
            d["rejected_reason"] = reason or "unspecified"
            drafts[i] = d
            save_corpus_drafts(drafts)
            _audit(
                draft_id, "corpus_draft_discarded",
                "corpus_drafts", "PRUNED",
                "Michael discarded: {0}".format(reason or "unspecified"),
                d.get("sms_score", 0),
            )
            return d
    return None


def get_pending_drafts() -> List[Dict]:
    drafts = load_corpus_drafts()
    return [d for d in drafts if d.get("status") == "pending"]


def get_draft(draft_id: str) -> Optional[Dict]:
    for d in load_corpus_drafts():
        if d["draft_id"] == draft_id:
            return d
    return None


def get_draft_history() -> List[Dict]:
    """Approved and rejected drafts, newest disposition first."""
    drafts = [d for d in load_corpus_drafts() if d.get("status") in ("approved", "discarded")]
    drafts.sort(
        key=lambda d: d.get("approved_at") or d.get("rejected_at") or d.get("created_at") or "",
        reverse=True,
    )
    return drafts


# ---------------------------------------------------------------------------
# Tier distribution summary
# ---------------------------------------------------------------------------

def get_tier_status() -> Dict:
    """Return a summary of tier distribution for `clara memory status`."""
    assignments = load_tier_assignments()
    counts: Dict[str, int] = {t.value: 0 for t in MemoryTier}
    pinned = 0

    for rec in assignments.values():
        tier = rec.get("tier", MemoryTier.EPHEMERAL_BUFFER.value)
        counts[tier] = counts.get(tier, 0) + 1
        if rec.get("pinned"):
            pinned += 1

    pending_drafts = len(get_pending_drafts())

    return {
        "tier_counts": counts,
        "pinned_count": pinned,
        "pending_corpus_drafts": pending_drafts,
        "total_tracked": len(assignments),
        "as_of": _now_iso(),
    }
