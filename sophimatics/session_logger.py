"""
Session Logger — Structured Daily Session Logs for the Sophimatics Loop

Writes every chat exchange to a daily JSONL file at backend/data/sessions/YYYY-MM-DD.jsonl.
These logs are the raw material for the nightly consolidation loop.

Unlike background_rag_write() which stores embeddings in ChromaDB (losing session structure),
this preserves the temporal sequence and metadata needed for pattern extraction.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

SESSIONS_DIR = Path(__file__).parent.parent / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _today_log_path() -> Path:
    return SESSIONS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"


def log_exchange(
    user_message: str,
    assistant_response: str,
    importance: float = 5.0,
    session_type: Optional[str] = None,
    mode: str = "chat",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a single exchange to today's session log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
        "assistant_response": assistant_response,
        "importance": importance,
        "session_type": session_type,
        "mode": mode,
        "tags": tags or [],
        "metadata": metadata or {},
    }
    with open(_today_log_path(), "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def read_day_log(date_str: Optional[str] = None) -> List[Dict]:
    """Read all exchanges for a given day (default: today). Returns list of dicts."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    path = SESSIONS_DIR / f"{date_str}.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def list_available_dates() -> List[str]:
    """Return sorted list of dates with session logs."""
    dates = []
    for f in SESSIONS_DIR.glob("*.jsonl"):
        dates.append(f.stem)
    return sorted(dates)


def get_day_summary_stats(date_str: Optional[str] = None) -> Dict[str, Any]:
    """Quick stats for a day's sessions."""
    entries = read_day_log(date_str)
    if not entries:
        return {"exchange_count": 0, "date": date_str}
    return {
        "date": date_str or datetime.now().strftime("%Y-%m-%d"),
        "exchange_count": len(entries),
        "first_exchange": entries[0]["timestamp"],
        "last_exchange": entries[-1]["timestamp"],
        "avg_importance": sum(e["importance"] for e in entries) / len(entries),
        "modes": list(set(e.get("mode", "chat") for e in entries)),
        "session_types": list(set(e.get("session_type") for e in entries if e.get("session_type"))),
    }
