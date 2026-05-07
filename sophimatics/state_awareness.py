"""
State Awareness Engine: Persistent Context Management

From "The Sovereign Prosthesis":
"Persistent State-Awareness: the ability to track ongoing projects,
recurring concerns, and unfinished business across sessions."

This module implements:
1. Project tracking across conversations
2. Logical vacancy detection (what remains unresolved)
3. Recurring concern monitoring
4. Context continuity across session boundaries
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum


class ProjectStatus(Enum):
    """Status of a tracked project."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ConcernPriority(Enum):
    """Priority level for recurring concerns."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TrackedProject:
    """A project being tracked across sessions."""
    id: str
    name: str
    description: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    milestones: List[Dict] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    related_topics: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['status'] = self.status.value
        d['created_at'] = self.created_at.isoformat()
        d['updated_at'] = self.updated_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'TrackedProject':
        d['status'] = ProjectStatus(d['status'])
        d['created_at'] = datetime.fromisoformat(d['created_at'])
        d['updated_at'] = datetime.fromisoformat(d['updated_at'])
        return cls(**d)


@dataclass
class RecurringConcern:
    """A concern that recurs across conversations."""
    id: str
    description: str
    priority: ConcernPriority
    first_mentioned: datetime
    last_mentioned: datetime
    mention_count: int
    context_snippets: List[str] = field(default_factory=list)
    resolution_attempts: List[Dict] = field(default_factory=list)
    resolved: bool = False

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['priority'] = self.priority.value
        d['first_mentioned'] = self.first_mentioned.isoformat()
        d['last_mentioned'] = self.last_mentioned.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'RecurringConcern':
        d['priority'] = ConcernPriority(d['priority'])
        d['first_mentioned'] = datetime.fromisoformat(d['first_mentioned'])
        d['last_mentioned'] = datetime.fromisoformat(d['last_mentioned'])
        return cls(**d)


@dataclass
class LogicalVacancy:
    """An unresolved question or gap in understanding."""
    id: str
    question: str
    context: str
    created_at: datetime
    blocking: List[str]  # Project IDs this blocks
    attempts: int = 0
    resolved: bool = False
    resolution: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['created_at'] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'LogicalVacancy':
        d['created_at'] = datetime.fromisoformat(d['created_at'])
        return cls(**d)


class StateAwarenessEngine:
    """
    Manages persistent state awareness across conversations.

    The key insight: a cognitive prosthesis must remember not just facts,
    but the USER'S relationship to those facts—what's being worked on,
    what's been left hanging, what keeps coming up.

    State persists to disk and loads on initialization.
    """

    def __init__(self, persist_path: str = "./state_awareness.json"):
        self.persist_path = Path(persist_path)
        self.projects: Dict[str, TrackedProject] = {}
        self.concerns: Dict[str, RecurringConcern] = {}
        self.vacancies: Dict[str, LogicalVacancy] = {}
        self.session_context: Dict[str, Any] = {}

        # Load persisted state
        self._load_state()

    def _load_state(self):
        """Load persisted state from disk."""
        if self.persist_path.exists():
            try:
                with open(self.persist_path, 'r') as f:
                    data = json.load(f)

                for pid, pdata in data.get('projects', {}).items():
                    self.projects[pid] = TrackedProject.from_dict(pdata)

                for cid, cdata in data.get('concerns', {}).items():
                    self.concerns[cid] = RecurringConcern.from_dict(cdata)

                for vid, vdata in data.get('vacancies', {}).items():
                    self.vacancies[vid] = LogicalVacancy.from_dict(vdata)

            except (json.JSONDecodeError, KeyError) as e:
                # Start fresh if corrupted
                pass

    def _save_state(self):
        """Persist state to disk."""
        data = {
            'projects': {k: v.to_dict() for k, v in self.projects.items()},
            'concerns': {k: v.to_dict() for k, v in self.concerns.items()},
            'vacancies': {k: v.to_dict() for k, v in self.vacancies.items()},
            'last_updated': datetime.now().isoformat()
        }

        with open(self.persist_path, 'w') as f:
            json.dump(data, f, indent=2)

    # === Project Management ===

    def track_project(
        self,
        name: str,
        description: str,
        related_topics: Optional[List[str]] = None
    ) -> TrackedProject:
        """Add or update a tracked project."""
        project_id = name.lower().replace(' ', '_')[:32]

        if project_id in self.projects:
            # Update existing
            project = self.projects[project_id]
            project.description = description
            project.updated_at = datetime.now()
            if related_topics:
                project.related_topics = list(set(
                    project.related_topics + related_topics
                ))
        else:
            # Create new
            project = TrackedProject(
                id=project_id,
                name=name,
                description=description,
                status=ProjectStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                related_topics=related_topics or []
            )
            self.projects[project_id] = project

        self._save_state()
        return project

    def update_project_status(
        self,
        project_id: str,
        status: ProjectStatus,
        note: Optional[str] = None
    ) -> Optional[TrackedProject]:
        """Update project status."""
        if project_id not in self.projects:
            return None

        project = self.projects[project_id]
        project.status = status
        project.updated_at = datetime.now()

        if note:
            project.notes = f"{project.notes}\n[{datetime.now().strftime('%Y-%m-%d')}] {note}".strip()

        self._save_state()
        return project

    def add_project_milestone(
        self,
        project_id: str,
        milestone: str,
        completed: bool = False
    ) -> Optional[TrackedProject]:
        """Add a milestone to a project."""
        if project_id not in self.projects:
            return None

        project = self.projects[project_id]
        project.milestones.append({
            "description": milestone,
            "completed": completed,
            "added_at": datetime.now().isoformat()
        })
        project.updated_at = datetime.now()

        self._save_state()
        return project

    def get_active_projects(self) -> List[TrackedProject]:
        """Get all active projects."""
        return [p for p in self.projects.values() if p.status == ProjectStatus.ACTIVE]

    # === Concern Tracking ===

    def track_concern(
        self,
        description: str,
        priority: ConcernPriority = ConcernPriority.MEDIUM,
        context_snippet: Optional[str] = None
    ) -> RecurringConcern:
        """Track a recurring concern."""
        concern_id = description.lower()[:32].replace(' ', '_')

        if concern_id in self.concerns:
            # Update existing
            concern = self.concerns[concern_id]
            concern.last_mentioned = datetime.now()
            concern.mention_count += 1
            if context_snippet:
                concern.context_snippets.append(context_snippet)
                concern.context_snippets = concern.context_snippets[-5:]  # Keep recent
        else:
            # Create new
            concern = RecurringConcern(
                id=concern_id,
                description=description,
                priority=priority,
                first_mentioned=datetime.now(),
                last_mentioned=datetime.now(),
                mention_count=1,
                context_snippets=[context_snippet] if context_snippet else []
            )
            self.concerns[concern_id] = concern

        self._save_state()
        return concern

    def get_unresolved_concerns(
        self,
        min_priority: ConcernPriority = ConcernPriority.LOW
    ) -> List[RecurringConcern]:
        """Get unresolved concerns at or above priority level."""
        priority_order = [
            ConcernPriority.CRITICAL,
            ConcernPriority.HIGH,
            ConcernPriority.MEDIUM,
            ConcernPriority.LOW
        ]
        min_index = priority_order.index(min_priority)
        allowed = priority_order[:min_index + 1]

        return [
            c for c in self.concerns.values()
            if not c.resolved and c.priority in allowed
        ]

    # === Logical Vacancy Tracking ===

    def note_vacancy(
        self,
        question: str,
        context: str,
        blocking: Optional[List[str]] = None
    ) -> LogicalVacancy:
        """Note an unresolved question or logical gap."""
        vacancy_id = question[:32].lower().replace(' ', '_')

        if vacancy_id in self.vacancies:
            # Increment attempts
            vacancy = self.vacancies[vacancy_id]
            vacancy.attempts += 1
        else:
            vacancy = LogicalVacancy(
                id=vacancy_id,
                question=question,
                context=context,
                created_at=datetime.now(),
                blocking=blocking or []
            )
            self.vacancies[vacancy_id] = vacancy

        self._save_state()
        return vacancy

    def resolve_vacancy(
        self,
        vacancy_id: str,
        resolution: str
    ) -> Optional[LogicalVacancy]:
        """Mark a logical vacancy as resolved."""
        if vacancy_id not in self.vacancies:
            return None

        vacancy = self.vacancies[vacancy_id]
        vacancy.resolved = True
        vacancy.resolution = resolution

        self._save_state()
        return vacancy

    def get_blocking_vacancies(self, project_id: str) -> List[LogicalVacancy]:
        """Get vacancies blocking a specific project."""
        return [
            v for v in self.vacancies.values()
            if project_id in v.blocking and not v.resolved
        ]

    # === Context Management ===

    def set_session_context(self, key: str, value: Any):
        """Set a piece of session context."""
        self.session_context[key] = value

    def get_session_context(self, key: str, default: Any = None) -> Any:
        """Get a piece of session context."""
        return self.session_context.get(key, default)

    def get_current_state_summary(self) -> Dict:
        """
        Generate a summary of current state for context injection.

        This is what gets injected into prompts to maintain
        persistent state awareness.
        """
        active_projects = self.get_active_projects()
        unresolved_concerns = self.get_unresolved_concerns(ConcernPriority.HIGH)
        open_vacancies = [v for v in self.vacancies.values() if not v.resolved]

        return {
            "active_projects": [
                {"name": p.name, "description": p.description[:100]}
                for p in active_projects[:5]
            ],
            "high_priority_concerns": [
                {"description": c.description, "mentions": c.mention_count}
                for c in unresolved_concerns[:3]
            ],
            "open_questions": [
                {"question": v.question, "attempts": v.attempts}
                for v in open_vacancies[:3]
            ],
            "session_context": self.session_context
        }

    def format_state_for_prompt(self) -> str:
        """
        Format current state as text for prompt injection.
        """
        summary = self.get_current_state_summary()
        lines = ["[PERSISTENT STATE AWARENESS]"]

        if summary["active_projects"]:
            lines.append("\nActive Projects:")
            for p in summary["active_projects"]:
                lines.append(f"  - {p['name']}: {p['description']}")

        if summary["high_priority_concerns"]:
            lines.append("\nRecurring Concerns:")
            for c in summary["high_priority_concerns"]:
                lines.append(f"  - {c['description']} (mentioned {c['mentions']}x)")

        if summary["open_questions"]:
            lines.append("\nOpen Questions:")
            for v in summary["open_questions"]:
                lines.append(f"  - {v['question']}")

        if not any([
            summary["active_projects"],
            summary["high_priority_concerns"],
            summary["open_questions"]
        ]):
            lines.append("  No tracked state.")

        return "\n".join(lines)

    # === Detection from Conversation ===

    def detect_project_mention(
        self,
        message: str,
        threshold: float = 0.5
    ) -> List[TrackedProject]:
        """
        Detect mentions of tracked projects in a message.

        Simple keyword matching for now—could be enhanced with
        semantic similarity.
        """
        mentioned = []
        message_lower = message.lower()

        for project in self.projects.values():
            # Check name
            if project.name.lower() in message_lower:
                mentioned.append(project)
                continue

            # Check related topics
            for topic in project.related_topics:
                if topic.lower() in message_lower:
                    mentioned.append(project)
                    break

        return mentioned

    def detect_concern_pattern(
        self,
        message: str,
        conversation_history: List[Dict]
    ) -> Optional[RecurringConcern]:
        """
        Detect if message represents a recurring concern pattern.

        Looks for themes that keep coming up across conversations.
        """
        # Simple pattern detection based on existing concerns
        message_lower = message.lower()

        for concern in self.concerns.values():
            # Check if concern topic appears
            concern_words = set(concern.description.lower().split())
            message_words = set(message_lower.split())
            overlap = len(concern_words & message_words)

            if overlap >= 2:  # At least 2 shared words
                # Update the concern
                return self.track_concern(
                    concern.description,
                    concern.priority,
                    message[:200]
                )

        return None
