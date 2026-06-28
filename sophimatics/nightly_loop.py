"""
Sophimatics Nightly Loop — Session Consolidation Engine

Runs nightly (configurable, default 2am) to:
  1. Read the day's session logs
  2. Extract behavioral patterns via local Ollama
  3. Identify what worked, what was corrected, what repeated
  4. Write consolidated learnings as structured playbooks
  5. Update MEMORY.md within the 200-line ceiling
  6. Prune contradicted and stale entries

This is the "Dreaming" equivalent — CLARA processes the day's sessions
and arrives at each new session already oriented by accumulated context.

Designed to interface with Anthropic's Managed Agents Dreaming feature
when access is approved. Local-first, API-ready.
"""

import asyncio
import json
import os
import re
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from sophimatics.session_logger import read_day_log, get_day_summary_stats
from sophimatics.memory_manager import (
    add_entries,
    read_memory,
    get_memory_stats,
    initialize_memory,
    SECTIONS,
)

logger = logging.getLogger("clara.sophimatics.nightly")

PLAYBOOKS_DIR = Path(__file__).parent.parent / "data" / "playbooks"
PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)

NIGHTLY_RUN_HOUR = int(os.getenv("SOPHIMATICS_NIGHTLY_HOUR", "2"))  # 2am local

# num_ctx tiers for the empty-body retry. Cloud-routed models tend to auto-
# scale or ignore num_ctx; local models honor it strictly and return Ollama's
# zero-value (200 OK, empty content, done=False) when the prompt+chat-template
# wrapper overflows. Same failure mode RLM handles at rlm_agent.py:884.
# Tiers clipped to config.NUM_CTX_CEILING at call time.
_NUM_CTX_TIERS = [8192, 16384, 32768]

PATTERN_EXTRACTION_PROMPT = """/no_think
You are analyzing a day's conversation logs between Michael and Clara (his AI assistant).
Your job is to extract PATTERNS — not summaries. Focus on:

1. **Behavioral Patterns**: How Michael works, thinks, communicates. Recurring approaches.
2. **Workflow Preferences**: Tools, sequences, formats he gravitates toward.
3. **Corrections**: Things Clara got wrong that Michael corrected. Lessons.
4. **Project Progress**: What moved forward, what's blocked, what's next.
5. **Insights**: Novel ideas, connections, or realizations that emerged.

Rules:
- Each finding must be a single concrete sentence starting with "- "
- Include the date as [YYYY-MM-DD] at the start of each entry
- No vague observations. "Michael prefers X" must cite the specific instance.
- Corrections are HIGH PRIORITY — never repeat a mistake Clara already learned from.
- Maximum 20 entries total across all categories.

Categorize each entry under exactly one of these sections:
- Active Projects
- Behavioral Patterns
- Workflow Preferences
- Corrections & Revisions
- Session Insights
- Accumulated Context

Format your response as:

## Active Projects
- [YYYY-MM-DD] entry here

## Behavioral Patterns
- [YYYY-MM-DD] entry here

(etc. — only include sections with entries)

Day's exchanges:
{exchanges}"""

PLAYBOOK_PROMPT = """/no_think
You are writing a structured playbook entry based on patterns extracted from today's sessions.
A playbook is a reusable guide for a specific workflow or project area.

Given these patterns and session context, write a playbook entry that captures:
1. What the workflow/project IS (one sentence)
2. Key decisions made (bulleted)
3. What works (proven approaches)
4. What to avoid (learned mistakes)
5. Next steps (if identifiable)

Keep it under 40 lines. Be concrete and actionable. No fluff.

Today's date: {date}
Patterns:
{patterns}

Session context:
{context}"""


def _call_ollama(
    prompt: str,
    ollama_host: str = "http://localhost:11434",
    *,
    models: List[str],
) -> Optional[str]:
    """Call Ollama with cloud-first cascade + num_ctx tier retry.

    Iterates `models` in order, returning the first non-empty response.
    Per-model timeout: 60s for cloud-suffixed models (warm; should respond
    fast), 300s for local models (cold-start budget under MAX_LOADED_MODELS=1).

    Per model, if the response is empty AND done=False (Ollama's zero-value
    signature for prompt+grammar overflowing num_ctx), retry once with the
    next tier up. This matches RLM's behavior at rlm_agent.py:884 — local
    models honor num_ctx strictly and overflow silently rather than erroring.
    Every failure is logged at WARNING so the cascade is visible in the log.
    """
    def _post(model: str, num_ctx: int, timeout: float):
        return requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": num_ctx, "temperature": 0.3},
            },
            timeout=timeout,
        )

    for model in models:
        timeout = 60.0 if model.endswith(":cloud") else 300.0
        try:
            initial_ctx = _NUM_CTX_TIERS[0]
            resp = _post(model, initial_ctx, timeout)
            if resp.status_code != 200:
                logger.warning(f"[sophimatics] {model} HTTP {resp.status_code} — trying next")
                continue
            data = resp.json()
            content = (data.get("response") or "").strip()

            # Ollama zero-value retry: empty content + done=False means the
            # prompt overflowed num_ctx silently. Bump one tier and retry.
            if not content and not data.get("done"):
                next_ctx = next((t for t in _NUM_CTX_TIERS if t > initial_ctx), None)
                if next_ctx is not None:
                    logger.warning(
                        f"[sophimatics] {model} num_ctx={initial_ctx} undersize "
                        f"(empty zero-value), retrying with num_ctx={next_ctx}"
                    )
                    resp = _post(model, next_ctx, timeout)
                    if resp.status_code == 200:
                        content = (resp.json().get("response") or "").strip()

            if content:
                logger.info(f"[sophimatics] {model} responded ({len(content)} chars)")
                return content
            logger.warning(f"[sophimatics] {model} returned empty body — trying next")
        except Exception as e:
            logger.warning(f"[sophimatics] {model} failed: {e!r} — trying next")
    return None


def _format_exchanges_for_prompt(entries: List[Dict], max_chars: int = 12000) -> str:
    """Format session log entries for the extraction prompt, respecting context limits."""
    formatted = []
    total_chars = 0
    for entry in entries:
        line = f"[{entry.get('timestamp', '?')}] User: {entry['user_message'][:300]}\nClara: {entry['assistant_response'][:300]}\n"
        if total_chars + len(line) > max_chars:
            break
        formatted.append(line)
        total_chars += len(line)
    return "\n".join(formatted)


def _parse_extraction_response(response: str) -> Dict[str, List[str]]:
    """Parse the LLM's structured extraction into section -> entries."""
    sections: Dict[str, List[str]] = {}
    current_section = None
    for line in response.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            section_name = stripped[3:].strip()
            if section_name in SECTIONS:
                current_section = section_name
                if current_section not in sections:
                    sections[current_section] = []
        elif stripped.startswith("- ") and current_section:
            sections[current_section].append(stripped)
    return sections


def extract_patterns(
    date_str: Optional[str] = None,
    ollama_host: str = "http://localhost:11434",
    *,
    models: List[str],
) -> Dict[str, List[str]]:
    """
    Extract behavioral patterns from a day's session logs.
    Returns dict of section -> list of entries.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    entries = read_day_log(date_str)
    if not entries:
        logger.info(f"No session logs for {date_str}")
        return {}

    exchanges_text = _format_exchanges_for_prompt(entries)
    prompt = PATTERN_EXTRACTION_PROMPT.format(exchanges=exchanges_text)

    response = _call_ollama(prompt, ollama_host, models=models)
    if not response:
        logger.error("Pattern extraction failed — no LLM response")
        return {}

    patterns = _parse_extraction_response(response)
    logger.info(f"Extracted {sum(len(v) for v in patterns.values())} patterns from {len(entries)} exchanges")
    return patterns


def generate_playbook(
    patterns: Dict[str, List[str]],
    date_str: Optional[str] = None,
    entries: Optional[List[Dict]] = None,
    ollama_host: str = "http://localhost:11434",
    *,
    models: List[str],
) -> Optional[Path]:
    """Generate a structured playbook from extracted patterns."""
    if not patterns:
        return None

    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    patterns_text = "\n".join(
        f"[{section}] {entry}"
        for section, entries_list in patterns.items()
        for entry in entries_list
    )

    context = ""
    if entries:
        context = _format_exchanges_for_prompt(entries[:5], max_chars=3000)

    prompt = PLAYBOOK_PROMPT.format(
        date=date_str,
        patterns=patterns_text,
        context=context,
    )

    response = _call_ollama(prompt, ollama_host, models=models)
    if not response:
        return None

    playbook_path = PLAYBOOKS_DIR / f"playbook_{date_str}.md"
    playbook_path.write_text(f"# Playbook — {date_str}\n\n{response}\n")
    logger.info(f"Playbook written: {playbook_path}")
    return playbook_path


def run_nightly_consolidation(
    date_str: Optional[str] = None,
    ollama_host: str = "http://localhost:11434",
    *,
    models: List[str],
    use_llm_contradiction: bool = True,
) -> Dict[str, Any]:
    """
    Full nightly consolidation pipeline:
    1. Read session logs
    2. Extract patterns
    3. Generate playbook
    4. Update MEMORY.md
    5. Return stats

    This is the core Sophimatics loop.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"=== Sophimatics Nightly Loop: {date_str} ===")
    initialize_memory()

    # Step 1: Read session logs
    entries = read_day_log(date_str)
    if not entries:
        logger.info(f"No sessions to consolidate for {date_str}")
        return {"date": date_str, "status": "no_sessions", "exchanges": 0}

    stats = get_day_summary_stats(date_str)
    logger.info(f"Processing {stats['exchange_count']} exchanges")

    # Step 2: Extract patterns
    patterns = extract_patterns(date_str, ollama_host, models=models)
    if not patterns:
        logger.warning("No patterns extracted — skipping consolidation")
        return {"date": date_str, "status": "no_patterns", "exchanges": stats["exchange_count"]}

    # Step 3: Generate playbook
    playbook_path = generate_playbook(patterns, date_str, entries, ollama_host, models=models)

    # Step 4: Update MEMORY.md
    memory_result = add_entries(
        patterns,
        use_llm_contradiction=use_llm_contradiction,
        ollama_host=ollama_host,
        models=models,
    )

    # Step 5: Report
    result = {
        "date": date_str,
        "status": "completed",
        "exchanges": stats["exchange_count"],
        "patterns_extracted": sum(len(v) for v in patterns.values()),
        "memory_update": memory_result,
        "playbook": str(playbook_path) if playbook_path else None,
        "memory_stats": get_memory_stats(),
        "completed_at": datetime.now().isoformat(),
    }
    logger.info(f"Nightly consolidation complete: {result['patterns_extracted']} patterns, "
                f"{memory_result['total_lines']}/200 memory lines")
    return result


async def nightly_loop_task(
    ollama_host: str = "http://localhost:11434",
    *,
    models: List[str],
):
    """
    Async background task that runs the nightly consolidation.
    Designed to be started alongside the Exploration Scheduler in main.py lifespan.
    """
    logger.info(f"Sophimatics nightly loop started (scheduled: {NIGHTLY_RUN_HOUR}:00)")
    while True:
        try:
            now = datetime.now()
            # Calculate time until next run
            if now.hour < NIGHTLY_RUN_HOUR:
                next_run = now.replace(hour=NIGHTLY_RUN_HOUR, minute=0, second=0, microsecond=0)
            else:
                tomorrow = now + timedelta(days=1)
                next_run = tomorrow.replace(hour=NIGHTLY_RUN_HOUR, minute=0, second=0, microsecond=0)

            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"Next nightly run at {next_run.strftime('%Y-%m-%d %H:%M')} "
                       f"({wait_seconds/3600:.1f} hours)")
            await asyncio.sleep(wait_seconds)

            # Run consolidation for yesterday (the day that just ended)
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            result = run_nightly_consolidation(yesterday, ollama_host, models=models)
            logger.info(f"Nightly loop result: {json.dumps(result, default=str)}")

        except asyncio.CancelledError:
            logger.info("Nightly loop cancelled")
            break
        except Exception as e:
            logger.error(f"Nightly loop error: {e}")
            await asyncio.sleep(300)  # wait 5min on error, then retry


class SophimaticsNightlyLoop:
    """Manager for the nightly consolidation background task."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        *,
        models: List[str],
    ):
        self.ollama_host = ollama_host
        self.models = models
        self._task: Optional[asyncio.Task] = None
        self.is_running = False

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(
            nightly_loop_task(self.ollama_host, models=self.models)
        )
        self.is_running = True
        logger.info("Sophimatics nightly loop started")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            self.is_running = False
            logger.info("Sophimatics nightly loop stopped")

    def get_status(self) -> Dict[str, Any]:
        now = datetime.now()
        if now.hour < NIGHTLY_RUN_HOUR:
            next_run = now.replace(hour=NIGHTLY_RUN_HOUR, minute=0, second=0, microsecond=0)
        else:
            tomorrow = now + timedelta(days=1)
            next_run = tomorrow.replace(hour=NIGHTLY_RUN_HOUR, minute=0, second=0, microsecond=0)
        return {
            "running": self.is_running,
            "nightly_hour": NIGHTLY_RUN_HOUR,
            "next_run": next_run.isoformat(),
            "hours_until_next": round((next_run - now).total_seconds() / 3600, 1),
            "memory_stats": get_memory_stats(),
        }
