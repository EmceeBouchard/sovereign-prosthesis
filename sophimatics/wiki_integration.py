"""
Wiki-to-Sophimatics Integration

Bridges the wiki knowledge base with the Ur-Codex and TemporalWeightingEngine.

The wiki is no longer a parallel knowledge base—it becomes a structured substrate
that the Sophimatics engines reason over. Each wiki page carries metadata that
informs the two-dimensional weighting:

- importance: 0-10 experiential significance
- temporal_status: persistent | emergent | active | deprecated
- disposition: axiomatic | dialectic | praxis | specimen

The disposition field tells the Russellian OS how to engage:
- axiomatic: Accept as foundation, low friction
- dialectic: Engage critically, high friction
- praxis: Operational knowledge, moderate friction
- specimen: Evidence/examples, context-dependent
"""

import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .temporal_weighting import TemporalWeightingEngine, WeightedDocument
from .ur_codex import UrCodexManager


@dataclass
class WikiPageMeta:
    """Sophimatics metadata for a wiki page."""
    page_id: str
    title: str
    path: str
    category: str

    # Sophimatics dimensions
    importance: float  # 0-10
    temporal_status: str  # persistent | emergent | active | deprecated
    disposition: str  # axiomatic | dialectic | praxis | specimen

    # Additional context
    date_established: Optional[datetime] = None
    last_validated: Optional[datetime] = None
    wikilinks: List[str] = None

    def __post_init__(self):
        if self.wikilinks is None:
            self.wikilinks = []


# Default importance scores by category and known pages
DEFAULT_IMPORTANCE = {
    # Foundational - 10/10
    "what-i-believe": 10.0,
    "engineers-watching-witch-trial": 10.0,
    "michael-bouchard": 10.0,

    # Core identity - 9/10
    "codex-clara": 9.0,
    "clara": 9.0,
    "russellian-os": 9.0,
    "etched-plate-animals": 9.0,
    "sovereign-prosthesis": 9.0,

    # High importance - 8/10
    "applied-humor-theory": 8.0,
    "the-coder-philosopher": 8.0,
    "hot": 8.0,
    "retrieval-guide": 8.0,

    # Active projects - 7/10
    "clara-v3": 7.0,
    "storytender": 7.0,
    "iacap-2026": 7.0,
    "dolphin-llama": 7.0,

    # Works and supporting - 6/10
    "villains": 6.0,
    "poetry-collection": 6.0,
    "mary-and-nigel": 6.0,
    "the-relic": 6.0,
    "only-the-best": 6.0,

    # Reference/indexes - 5/10
    "clean-entities": 5.0,
    "timestamp-anchors": 5.0,
    "index": 5.0,
    "log": 4.0,

    # Sources (raw corpus pointers) - 4/10
    "transfer-packets": 4.0,
    "psychological-assessments": 4.0,
    "creative-writing": 4.0,
    "openai-archive": 4.0,
}

# Temporal status by category
DEFAULT_TEMPORAL_STATUS = {
    "entities": "persistent",
    "concepts": "persistent",
    "works": "persistent",
    "projects": "active",
    "sources": "persistent",
    "indexes": "active",
    "root": "active",
}

# Disposition by category and page
DEFAULT_DISPOSITION = {
    # Axiomatic - accept as foundation
    "what-i-believe": "axiomatic",
    "engineers-watching-witch-trial": "axiomatic",
    "michael-bouchard": "axiomatic",
    "etched-plate-animals": "axiomatic",

    # Dialectic - engage critically
    "russellian-os": "dialectic",
    "codex-clara": "dialectic",
    "applied-humor-theory": "dialectic",
    "sovereign-prosthesis": "dialectic",

    # Praxis - operational
    "clara-v3": "praxis",
    "storytender": "praxis",
    "iacap-2026": "praxis",
    "hot": "praxis",
    "retrieval-guide": "praxis",

    # Specimen - evidence/examples
    "villains": "specimen",
    "poetry-collection": "specimen",
    "mary-and-nigel": "specimen",
    "the-relic": "specimen",
    "clean-entities": "specimen",
    "timestamp-anchors": "specimen",
}

# Category defaults
CATEGORY_DISPOSITION = {
    "entities": "axiomatic",
    "concepts": "dialectic",
    "works": "specimen",
    "projects": "praxis",
    "sources": "specimen",
    "indexes": "praxis",
    "root": "praxis",
}


class WikiSophimaticsEngine:
    """
    Integrates the wiki with Sophimatics infrastructure.

    Responsibilities:
    1. Parse wiki pages and extract/assign Sophimatics metadata
    2. Ingest wiki pages into the Ur-Codex with proper weighting
    3. Provide weighted retrieval over wiki content
    4. Support the Russellian OS by signaling disposition
    """

    def __init__(
        self,
        wiki_path: str,
        ur_codex: Optional[UrCodexManager] = None,
        temporal_engine: Optional[TemporalWeightingEngine] = None
    ):
        self.wiki_path = Path(wiki_path)
        self.ur_codex = ur_codex
        self.temporal_engine = temporal_engine or TemporalWeightingEngine()

        # Cache of parsed pages
        self._page_cache: Dict[str, WikiPageMeta] = {}

    def _parse_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter from markdown content."""
        if not content.startswith('---'):
            return {}, content

        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}, content

        try:
            frontmatter = yaml.safe_load(parts[1])
            return frontmatter or {}, parts[2]
        except yaml.YAMLError:
            return {}, content

    def _extract_wikilinks(self, content: str) -> List[str]:
        """Extract all [[wikilinks]] from content."""
        return re.findall(r'\[\[([^\]]+)\]\]', content)

    def _get_importance(self, page_id: str, category: str, frontmatter: Dict) -> float:
        """Determine importance score for a page."""
        # Check frontmatter first
        if 'importance' in frontmatter:
            return float(frontmatter['importance'])

        # Check known pages
        if page_id in DEFAULT_IMPORTANCE:
            return DEFAULT_IMPORTANCE[page_id]

        # Category defaults
        category_defaults = {
            "entities": 7.0,
            "concepts": 8.0,
            "works": 6.0,
            "projects": 7.0,
            "sources": 4.0,
            "indexes": 5.0,
            "root": 6.0,
        }
        return category_defaults.get(category, 5.0)

    def _get_temporal_status(self, page_id: str, category: str, frontmatter: Dict) -> str:
        """Determine temporal status for a page."""
        if 'temporal_status' in frontmatter:
            return frontmatter['temporal_status']
        return DEFAULT_TEMPORAL_STATUS.get(category, 'active')

    def _get_disposition(self, page_id: str, category: str, frontmatter: Dict) -> str:
        """Determine epistemic disposition for a page."""
        if 'disposition' in frontmatter:
            return frontmatter['disposition']
        if page_id in DEFAULT_DISPOSITION:
            return DEFAULT_DISPOSITION[page_id]
        return CATEGORY_DISPOSITION.get(category, 'praxis')

    def parse_page(self, page_path: Path) -> WikiPageMeta:
        """Parse a wiki page and extract Sophimatics metadata."""
        content = page_path.read_text(encoding='utf-8')
        frontmatter, body = self._parse_frontmatter(content)

        # Determine category from path
        relative = page_path.relative_to(self.wiki_path)
        category = str(relative.parent) if relative.parent != Path('.') else 'root'

        page_id = page_path.stem

        # Extract title from first heading
        title_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
        title = title_match.group(1) if title_match else page_id

        # Build metadata
        meta = WikiPageMeta(
            page_id=page_id,
            title=title,
            path=str(relative).replace('.md', ''),
            category=category,
            importance=self._get_importance(page_id, category, frontmatter),
            temporal_status=self._get_temporal_status(page_id, category, frontmatter),
            disposition=self._get_disposition(page_id, category, frontmatter),
            date_established=frontmatter.get('date_established'),
            last_validated=frontmatter.get('last_validated'),
            wikilinks=self._extract_wikilinks(body)
        )

        self._page_cache[page_id] = meta
        return meta

    def scan_wiki(self) -> Dict[str, WikiPageMeta]:
        """Scan all wiki pages and build metadata index."""
        pages = {}

        for md_file in self.wiki_path.rglob('*.md'):
            try:
                meta = self.parse_page(md_file)
                pages[meta.page_id] = meta
            except Exception as e:
                print(f"Error parsing {md_file}: {e}")

        return pages

    def ingest_to_urcodex(self) -> int:
        """
        Ingest all wiki pages into the Ur-Codex.

        Each page becomes a document with Sophimatics metadata
        that the TemporalWeightingEngine can use for retrieval.
        """
        if not self.ur_codex:
            raise ValueError("UrCodexManager not configured")

        ingested = 0

        for md_file in self.wiki_path.rglob('*.md'):
            try:
                content = md_file.read_text(encoding='utf-8')
                meta = self.parse_page(md_file)

                # Generate document ID
                doc_id = f"wiki:{meta.page_id}"

                # Ingest with Sophimatics metadata
                self.ur_codex.collection.upsert(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[{
                        "source_file": str(md_file),
                        "doc_type": "wiki",
                        "title": meta.title,
                        "page_id": meta.page_id,
                        "category": meta.category,
                        "importance_score": meta.importance,
                        "temporal_status": meta.temporal_status,
                        "disposition": meta.disposition,
                        "wikilinks": ",".join(meta.wikilinks),
                        "ingested_at": datetime.now().isoformat()
                    }]
                )
                ingested += 1

            except Exception as e:
                print(f"Error ingesting {md_file}: {e}")

        return ingested

    def weighted_search(
        self,
        query: str,
        n_results: int = 10,
        min_importance: float = 0.0,
        disposition_filter: Optional[List[str]] = None
    ) -> List[WeightedDocument]:
        """
        Search wiki with Sophimatic two-dimensional weighting.

        Returns documents ranked by combined weight of:
        - Semantic similarity
        - Experiential significance (importance)
        - Chronological recency
        """
        if not self.ur_codex:
            raise ValueError("UrCodexManager not configured")

        # Query Ur-Codex for wiki documents
        raw_results = self.ur_codex.query(
            query_text=query,
            n_results=n_results * 2,  # Get more for filtering
            doc_types=["wiki"]
        )

        # Filter by importance if specified
        if min_importance > 0:
            raw_results = [
                doc for doc in raw_results
                if doc['metadata'].get('importance_score', 0) >= min_importance
            ]

        # Filter by disposition if specified
        if disposition_filter:
            raw_results = [
                doc for doc in raw_results
                if doc['metadata'].get('disposition') in disposition_filter
            ]

        # Apply two-dimensional weighting
        weighted = self.temporal_engine.weight_documents(raw_results)

        return weighted[:n_results]

    def get_page_with_meta(self, page_id: str) -> Tuple[str, WikiPageMeta]:
        """Get page content and full Sophimatics metadata."""
        # Find the page file
        candidates = [
            self.wiki_path / f"{page_id}.md",
        ]
        for subdir in ['entities', 'concepts', 'works', 'projects', 'sources', 'indexes']:
            candidates.append(self.wiki_path / subdir / f"{page_id}.md")

        for candidate in candidates:
            if candidate.exists():
                content = candidate.read_text(encoding='utf-8')
                meta = self.parse_page(candidate)
                return content, meta

        raise FileNotFoundError(f"Wiki page not found: {page_id}")

    def get_russellian_friction(self, disposition: str) -> str:
        """
        Return friction level for Russellian OS based on disposition.

        This tells the reasoning engine how to engage with the content:
        - axiomatic: LOW - accept as foundation
        - dialectic: HIGH - engage critically, challenge
        - praxis: MODERATE - verify but don't over-question
        - specimen: CONTEXT - depends on use case
        """
        friction_map = {
            "axiomatic": "LOW",
            "dialectic": "HIGH",
            "praxis": "MODERATE",
            "specimen": "CONTEXT"
        }
        return friction_map.get(disposition, "MODERATE")

    def generate_sophimatics_frontmatter(self, page_id: str, category: str) -> str:
        """Generate YAML frontmatter for a wiki page."""
        importance = self._get_importance(page_id, category, {})
        temporal_status = self._get_temporal_status(page_id, category, {})
        disposition = self._get_disposition(page_id, category, {})

        return f"""---
sophimatics:
  importance: {importance}
  temporal_status: {temporal_status}
  disposition: {disposition}
  last_validated: {datetime.now().strftime('%Y-%m-%d')}
---

"""


# Factory function for integration with main.py
def create_wiki_engine(
    wiki_path: str = "/Users/michaelbouchard/Desktop/Clara_Consolidated/03_CORPUS/wiki",
    ur_codex: Optional[UrCodexManager] = None,
    temporal_engine: Optional[TemporalWeightingEngine] = None
) -> WikiSophimaticsEngine:
    """Create a WikiSophimaticsEngine instance."""
    return WikiSophimaticsEngine(
        wiki_path=wiki_path,
        ur_codex=ur_codex,
        temporal_engine=temporal_engine
    )
