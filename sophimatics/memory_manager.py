"""
MEMORY.md Manager — Persistent Behavioral Pattern Layer

Manages backend/data/MEMORY.md with these invariants:
  - Hard ceiling of 200 lines
  - Absolute date conversion on every write (no relative dates)
  - Contradiction detection and deletion
  - Stale memory pruning (configurable TTL)
  - Overlapping entry merging
  - High-signal preservation (importance-weighted)
  - Structured for Anthropic Dreaming interface readiness

MEMORY.md is injected into the system prompt at session start,
giving CLARA accumulated behavioral context before the first query.
"""

import json
import logging
import os
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

MAX_LINES = 200
STALE_DAYS = 30  # entries older than this without refresh get pruned
MEMORY_PATH = Path(__file__).parent.parent / "data" / "MEMORY.md"

# Sections in MEMORY.md — order matters for prompt injection
SECTIONS = [
    "Active Projects",
    "Behavioral Patterns",
    "Workflow Preferences",
    "Corrections & Revisions",
    "Session Insights",
    "Accumulated Context",
]

HEADER = """# MEMORY.md — Clara's Learned Context
# Auto-managed by Sophimatics nightly loop. Do not edit manually.
# Last updated: {updated}
# Line count: {line_count}/200
"""


def _load_memory() -> str:
    if MEMORY_PATH.exists():
        return MEMORY_PATH.read_text()
    return ""


def _save_memory(content: str) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(content)


def _count_lines(content: str) -> int:
    return len([l for l in content.split("\n") if l.strip()])


def _parse_sections(content: str) -> Dict[str, List[str]]:
    """Parse MEMORY.md into section -> list of entries."""
    sections: Dict[str, List[str]] = {s: [] for s in SECTIONS}
    current_section = None
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("# MEMORY.md") or stripped.startswith("# Auto-managed") or stripped.startswith("# Last updated") or stripped.startswith("# Line count"):
            continue
        matched_section = None
        for s in SECTIONS:
            if stripped == f"## {s}":
                matched_section = s
                break
        if matched_section:
            current_section = matched_section
            continue
        if current_section and stripped.startswith("- "):
            sections[current_section].append(stripped)
        elif current_section and sections[current_section]:
            sections[current_section][-1] += " " + stripped
    return sections


def _render_sections(sections: Dict[str, List[str]]) -> str:
    """Render sections dict back to markdown."""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = sum(len(entries) for entries in sections.values())
    lines.append(HEADER.format(updated=now, line_count=total + len(SECTIONS) + 5).strip())
    lines.append("")
    for section_name in SECTIONS:
        entries = sections.get(section_name, [])
        if entries:
            lines.append(f"## {section_name}")
            for entry in entries:
                lines.append(entry)
            lines.append("")
    return "\n".join(lines)


def convert_relative_dates(text: str) -> str:
    """Convert relative date references to absolute dates."""
    now = datetime.now()
    replacements = {
        "today": now.strftime("%Y-%m-%d"),
        "yesterday": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
        "tomorrow": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
        "last week": (now - timedelta(weeks=1)).strftime("week of %Y-%m-%d"),
        "this week": now.strftime("week of %Y-%m-%d"),
        "next week": (now + timedelta(weeks=1)).strftime("week of %Y-%m-%d"),
        "last month": (now - timedelta(days=30)).strftime("%Y-%m"),
        "this month": now.strftime("%Y-%m"),
    }
    result = text
    for relative, absolute in replacements.items():
        pattern = re.compile(re.escape(relative), re.IGNORECASE)
        result = pattern.sub(absolute, result)
    return result


def _extract_date_from_entry(entry: str) -> Optional[datetime]:
    """Try to extract a date from an entry's bracketed prefix."""
    match = re.search(r'\[(\d{4}-\d{2}-\d{2})', entry)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    return None


def prune_stale_entries(sections: Dict[str, List[str]], max_age_days: int = STALE_DAYS) -> Dict[str, List[str]]:
    """Remove entries older than max_age_days that aren't high-signal."""
    cutoff = datetime.now() - timedelta(days=max_age_days)
    pruned = {}
    for section, entries in sections.items():
        kept = []
        for entry in entries:
            entry_date = _extract_date_from_entry(entry)
            if entry_date and entry_date < cutoff:
                # Keep high-signal entries (marked with !) even if stale
                if "!" not in entry and "CRITICAL" not in entry.upper():
                    continue
            kept.append(entry)
        pruned[section] = kept
    return pruned


def detect_contradictions_local(sections: Dict[str, List[str]]) -> List[Tuple[str, str, str]]:
    """
    Simple local contradiction detection without LLM.
    Finds entries in the same section that share key terms but have opposing signals.
    Returns list of (section, older_entry, newer_entry) tuples.
    """
    contradictions = []
    negation_pairs = [
        ("prefers", "avoids"), ("enable", "disable"), ("use", "don't use"),
        ("likes", "dislikes"), ("wants", "doesn't want"), ("always", "never"),
        ("switched to", "switched from"), ("adopted", "abandoned"),
    ]
    for section, entries in sections.items():
        for i, entry_a in enumerate(entries):
            for j, entry_b in enumerate(entries):
                if j <= i:
                    continue
                a_lower = entry_a.lower()
                b_lower = entry_b.lower()
                for pos, neg in negation_pairs:
                    if (pos in a_lower and neg in b_lower) or (neg in a_lower and pos in b_lower):
                        # Check if they share at least one significant word
                        words_a = set(re.findall(r'\b\w{4,}\b', a_lower))
                        words_b = set(re.findall(r'\b\w{4,}\b', b_lower))
                        shared = words_a & words_b
                        if len(shared) >= 2:
                            date_a = _extract_date_from_entry(entry_a)
                            date_b = _extract_date_from_entry(entry_b)
                            if date_a and date_b:
                                older, newer = (entry_a, entry_b) if date_a < date_b else (entry_b, entry_a)
                            else:
                                older, newer = entry_a, entry_b
                            contradictions.append((section, older, newer))
    return contradictions


def resolve_contradictions(sections: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Remove older contradicted entries, keeping the newer version."""
    contradictions = detect_contradictions_local(sections)
    to_remove = set()
    for section, older, newer in contradictions:
        to_remove.add((section, older))
    resolved = {}
    for section, entries in sections.items():
        resolved[section] = [e for e in entries if (section, e) not in to_remove]
    return resolved


def detect_contradictions_llm(
    sections: Dict[str, List[str]],
    ollama_host: str = "http://localhost:11434",
    *,
    models: List[str],
) -> List[Tuple[str, str]]:
    """
    Use Ollama to detect contradictions across all entries.
    Returns list of (section, entry_to_remove) tuples.

    Cascades through `models` cloud-first / local-fallback. Per-model
    timeout: 60s cloud / 300s local (cold-start budget). Every failure
    logs at WARNING for visibility.
    """
    all_entries = []
    for section, entries in sections.items():
        for entry in entries:
            all_entries.append(f"[{section}] {entry}")
    if len(all_entries) < 2:
        return []

    entries_text = "\n".join(f"{i+1}. {e}" for i, e in enumerate(all_entries))
    prompt = f"""Review these memory entries for contradictions. Two entries contradict if they make incompatible claims about the same topic — e.g., "prefers X" vs "switched away from X".

{entries_text}

List ONLY the line numbers of entries that are contradicted by a MORE RECENT entry (the older/superseded one should be removed). Return just the numbers separated by commas, or "none" if no contradictions found. /no_think"""

    # Tier-retry on Ollama zero-value (empty content + done=False = prompt
    # overflowed num_ctx). Imported lazily to avoid a top-of-module circular
    # if sophimatics submodules ever cross-import each other in different orders.
    from sophimatics.nightly_loop import _NUM_CTX_TIERS

    def _post(model: str, num_ctx: int, timeout: float):
        return requests.post(
            f"{ollama_host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"num_ctx": num_ctx}},
            timeout=timeout,
        )

    result_text: Optional[str] = None
    for model in models:
        timeout = 60.0 if model.endswith(":cloud") else 300.0
        try:
            initial_ctx = _NUM_CTX_TIERS[0]
            resp = _post(model, initial_ctx, timeout)
            if resp.status_code != 200:
                logger.warning(f"[sophimatics] {model} HTTP {resp.status_code} on contradiction-check — trying next")
                continue
            data = resp.json()
            content = (data.get("response") or "").strip().lower()

            if not content and not data.get("done"):
                next_ctx = next((t for t in _NUM_CTX_TIERS if t > initial_ctx), None)
                if next_ctx is not None:
                    logger.warning(
                        f"[sophimatics] {model} num_ctx={initial_ctx} undersize on "
                        f"contradiction-check, retrying with num_ctx={next_ctx}"
                    )
                    resp = _post(model, next_ctx, timeout)
                    if resp.status_code == 200:
                        content = (resp.json().get("response") or "").strip().lower()

            logger.info(f"[sophimatics] {model} contradiction-check ok")
            result_text = content
            break
        except Exception as e:
            logger.warning(f"[sophimatics] {model} failed on contradiction-check: {e!r} — trying next")

    if result_text is None or result_text == "none" or not result_text:
        return []

    numbers = re.findall(r'\d+', result_text)
    to_remove = []
    for num_str in numbers:
        idx = int(num_str) - 1
        if 0 <= idx < len(all_entries):
            entry_text = all_entries[idx]
            section_match = re.match(r'\[(.+?)\] (.+)', entry_text)
            if section_match:
                to_remove.append((section_match.group(1), section_match.group(2)))
    return to_remove


def enforce_line_ceiling(sections: Dict[str, List[str]], max_lines: int = MAX_LINES) -> Dict[str, List[str]]:
    """
    Trim to max_lines by removing lowest-signal entries.
    Priority (kept last): entries with !, CRITICAL, recent dates.
    """
    total = sum(len(entries) for entries in sections.values())
    overhead = len(SECTIONS) + 6  # headers + blank lines
    available = max_lines - overhead
    if total <= available:
        return sections

    all_scored = []
    for section, entries in sections.items():
        for entry in entries:
            score = 0.0
            if "!" in entry or "CRITICAL" in entry.upper():
                score += 10.0
            date = _extract_date_from_entry(entry)
            if date:
                days_old = (datetime.now() - date).days
                score += max(0, 30 - days_old) / 3.0  # recent = higher score
            else:
                score += 2.0  # undated entries get a modest default
            all_scored.append((section, entry, score))

    all_scored.sort(key=lambda x: x[2], reverse=True)
    kept = all_scored[:available]

    result = {s: [] for s in SECTIONS}
    for section, entry, _ in kept:
        result[section].append(entry)
    return result


def add_entries(
    new_entries: Dict[str, List[str]],
    use_llm_contradiction: bool = False,
    ollama_host: str = "http://localhost:11434",
    *,
    models: List[str],
) -> Dict[str, int]:
    """
    Add new entries to MEMORY.md with full pipeline:
    1. Convert relative dates to absolute
    2. Merge with existing
    3. Detect and resolve contradictions
    4. Prune stale entries
    5. Enforce 200-line ceiling
    6. Save

    Returns stats dict.
    """
    content = _load_memory()
    sections = _parse_sections(content) if content else {s: [] for s in SECTIONS}

    added = 0
    for section, entries in new_entries.items():
        if section not in sections:
            continue
        for entry in entries:
            entry = convert_relative_dates(entry)
            if not entry.startswith("- "):
                entry = f"- {entry}"
            # Add date prefix if not present
            if not re.search(r'\[\d{4}-\d{2}-\d{2}', entry):
                today = datetime.now().strftime("%Y-%m-%d")
                entry = entry[:2] + f"[{today}] " + entry[2:]
            sections[section].append(entry)
            added += 1

    # Contradiction resolution
    if use_llm_contradiction:
        llm_removals = detect_contradictions_llm(sections, ollama_host, models=models)
        for section, entry in llm_removals:
            if section in sections and entry in sections[section]:
                sections[section].remove(entry)
    sections = resolve_contradictions(sections)

    sections = prune_stale_entries(sections)
    sections = enforce_line_ceiling(sections)

    rendered = _render_sections(sections)
    _save_memory(rendered)

    total_lines = _count_lines(rendered)
    return {
        "entries_added": added,
        "total_lines": total_lines,
        "sections": {s: len(entries) for s, entries in sections.items()},
    }


def read_memory() -> str:
    """Read MEMORY.md content for session initialization injection."""
    return _load_memory()


def get_memory_stats() -> Dict[str, Any]:
    """Get current MEMORY.md statistics."""
    content = _load_memory()
    if not content:
        return {"exists": False, "line_count": 0, "sections": {}}
    sections = _parse_sections(content)
    return {
        "exists": True,
        "line_count": _count_lines(content),
        "max_lines": MAX_LINES,
        "sections": {s: len(entries) for s, entries in sections.items()},
        "path": str(MEMORY_PATH),
    }


def initialize_memory() -> None:
    """Create MEMORY.md with empty structure if it doesn't exist."""
    if MEMORY_PATH.exists():
        return
    sections = {s: [] for s in SECTIONS}
    rendered = _render_sections(sections)
    _save_memory(rendered)
