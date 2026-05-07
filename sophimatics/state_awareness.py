"""StateAwarenessEngine — persistent project and concern tracking.

Implements the operational criterion for proximal integration described
in Section 3 of The Sovereign Prosthesis. A prosthetic system must
maintain awareness of the user's active projects, recurring concerns,
and logical vacancies — the gaps in their thinking that have been noted
but not yet resolved.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Project:
    name: str
    description: str
    status: str = "active"  # active | paused | complete
    project_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecurringConcern:
    """A theme or question that surfaces repeatedly in the user's corpus."""
    concern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    summary: str = ""
    first_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    occurrence_count: int = 1
    related_project_ids: list[str] = field(default_factory=list)


@dataclass
class LogicalVacancy:
    """A gap in the user's thinking that has been identified but not resolved."""
    vacancy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    domain: str = ""
    identified_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    resolved: bool = False
    resolution_note: str = ""


@dataclass
class StateSnapshot:
    projects: list[Project]
    concerns: list[RecurringConcern]
    vacancies: list[LogicalVacancy]
    snapshot_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class StateAwarenessEngine:
    """Tracks active projects, recurring concerns, and logical vacancies.

    Persists state to a JSON file so awareness survives session boundaries —
    a precondition of genuine proximal integration.
    """

    def __init__(self, state_path: str = "./codex_state.json") -> None:
        self._path = Path(state_path)
        self._projects: dict[str, Project] = {}
        self._concerns: dict[str, RecurringConcern] = {}
        self._vacancies: dict[str, LogicalVacancy] = {}
        self._load()

    # --- Projects -----------------------------------------------------------

    def add_project(self, name: str, description: str, **kwargs) -> Project:
        p = Project(name=name, description=description, **kwargs)
        self._projects[p.project_id] = p
        self._save()
        return p

    def update_project_status(self, project_id: str, status: str) -> None:
        if project_id not in self._projects:
            raise KeyError(f"No project with id {project_id}")
        self._projects[project_id].status = status
        self._projects[project_id].updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

    def active_projects(self) -> list[Project]:
        return [p for p in self._projects.values() if p.status == "active"]

    # --- Recurring Concerns -------------------------------------------------

    def record_concern(self, summary: str, project_ids: list[str] | None = None) -> RecurringConcern:
        for concern in self._concerns.values():
            if concern.summary.lower() == summary.lower():
                concern.occurrence_count += 1
                concern.last_seen = datetime.now(timezone.utc).isoformat()
                self._save()
                return concern
        c = RecurringConcern(
            summary=summary,
            related_project_ids=project_ids or [],
        )
        self._concerns[c.concern_id] = c
        self._save()
        return c

    def top_concerns(self, n: int = 5) -> list[RecurringConcern]:
        return sorted(
            self._concerns.values(),
            key=lambda c: c.occurrence_count,
            reverse=True,
        )[:n]

    # --- Logical Vacancies --------------------------------------------------

    def note_vacancy(self, description: str, domain: str = "") -> LogicalVacancy:
        v = LogicalVacancy(description=description, domain=domain)
        self._vacancies[v.vacancy_id] = v
        self._save()
        return v

    def resolve_vacancy(self, vacancy_id: str, resolution_note: str = "") -> None:
        if vacancy_id not in self._vacancies:
            raise KeyError(f"No vacancy with id {vacancy_id}")
        self._vacancies[vacancy_id].resolved = True
        self._vacancies[vacancy_id].resolution_note = resolution_note
        self._save()

    def open_vacancies(self) -> list[LogicalVacancy]:
        return [v for v in self._vacancies.values() if not v.resolved]

    # --- Snapshot -----------------------------------------------------------

    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            projects=list(self._projects.values()),
            concerns=list(self._concerns.values()),
            vacancies=list(self._vacancies.values()),
        )

    # --- Persistence --------------------------------------------------------

    def _save(self) -> None:
        data = {
            "projects": {k: asdict(v) for k, v in self._projects.items()},
            "concerns": {k: asdict(v) for k, v in self._concerns.items()},
            "vacancies": {k: asdict(v) for k, v in self._vacancies.items()},
        }
        self._path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text())
        self._projects = {
            k: Project(**v) for k, v in data.get("projects", {}).items()
        }
        self._concerns = {
            k: RecurringConcern(**v) for k, v in data.get("concerns", {}).items()
        }
        self._vacancies = {
            k: LogicalVacancy(**v) for k, v in data.get("vacancies", {}).items()
        }
