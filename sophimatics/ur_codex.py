"""
Ur-Codex Manager: Longitudinal Memory Governance

The Ur-Codex is the complete conversational history that serves as
"world-historical context" for the cognitive prosthesis.

From "The Sovereign Prosthesis":
"The Ur-Codex—the longitudinal record of exchanges across years—
serves as a kind of world-historical context."

This module handles:
1. Ingesting the Complete Corpus (transfer packets, psychological profiles, creative work)
2. Maintaining the importance index for experiential weighting
3. Providing contextual retrieval that respects the full history
"""

import os
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import chromadb
from chromadb.config import Settings


# Significance scoring criteria for auto-classification
SIGNIFICANCE_CRITERIA = """You are scoring a document for the Sophimatics corpus.
Assign an importance_score from 1-10 using these criteria:

10 — Foundational philosophy. Establishes axioms that all
     other reasoning depends on. Example: a document defining
     the user's core worldview or ethical commitments.

9  — Core identity. Defines who the user is, how they think,
     what they value. Example: cognitive fingerprint,
     self-description, identity entity page.

8  — Active project architecture. Load-bearing decisions for
     something currently being built. Example: architectural
     decisions, design principles for ongoing work.

7  — Completed significant work. Finished creative or
     intellectual work with lasting relevance. Example:
     published papers, completed plays, finished essays.

6  — Active creative work. Work in progress with ongoing
     relevance. Example: drafts, working documents.

5  — Default. Conversations, notes, operational content
     without special significance.

1-4 — Low signal. Logistics, ephemera, one-off references
      with no lasting relevance.

Document to score:
{document_text}

Return only a single integer between 1 and 10."""


def auto_classify_significance(
    document_text: str,
    ollama_host: str = "http://localhost:11434",
    model: str = "llama3.2",
    timeout: float = 30.0
) -> float:
    """
    Use local Ollama LLM to auto-classify document importance.

    Reads the document text and asks the model to score it based on
    the SIGNIFICANCE_CRITERIA constant.

    Args:
        document_text: The full text of the document to classify
        ollama_host: Ollama API endpoint
        model: Model name to use for classification
        timeout: Request timeout in seconds

    Returns:
        importance_score: Float from 1.0-10.0, defaults to 5.0 on failure
    """
    # Truncate very long documents to avoid token limits
    max_chars = 4000
    text_sample = document_text[:max_chars]
    if len(document_text) > max_chars:
        text_sample += "\n\n[... document truncated for classification ...]"

    prompt = SIGNIFICANCE_CRITERIA.format(document_text=text_sample)

    try:
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent scoring
                    "num_predict": 10    # Only need a single number
                }
            },
            timeout=timeout
        )
        response.raise_for_status()

        result = response.json()
        answer = result.get("response", "").strip()

        # Parse the score - extract first number found
        import re
        match = re.search(r'\b(10|[1-9])\b', answer)
        if match:
            return float(match.group(1))

        # Fallback to default
        return 5.0

    except requests.exceptions.RequestException:
        # Ollama not available or request failed - return default
        return 5.0
    except (ValueError, KeyError):
        return 5.0


@dataclass
class CorpusDocument:
    """A document in the Ur-Codex."""
    id: str
    content: str
    source_file: str
    doc_type: str  # 'transfer_packet', 'psychological', 'creative', 'conversation'
    importance_score: float  # 0-10
    date: Optional[datetime]
    topics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class UrCodexManager:
    """
    Manages the Ur-Codex: the longitudinal conversational memory.

    The Ur-Codex is more than a database—it's the substrate of
    persistent state-awareness that makes the prosthesis continuous.

    Key responsibilities:
    1. Ingest and index the Complete Corpus
    2. Maintain importance scores for Sophimatic weighting
    3. Track document provenance (source, date, type)
    4. Provide retrieval interface for the weighting engine
    """

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "ur_codex",
        corpus_path: Optional[str] = None,
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "llama3.2",
        auto_classify: bool = True
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.corpus_path = corpus_path
        self.ollama_host = ollama_host
        self.ollama_model = ollama_model
        self.auto_classify = auto_classify

        # Initialize ChromaDB with telemetry disabled to prevent posthog version conflicts
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection (uses default embedding function)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        # Cache for importance index
        self._importance_index: Dict[str, float] = {}

    def _get_importance_score(
        self,
        content: str,
        explicit_score: Optional[float] = None,
        default_score: float = 5.0
    ) -> float:
        """
        Get importance score for a document.

        Priority:
        1. Explicit score if provided (manual override)
        2. Auto-classification via Ollama if enabled
        3. Default score as fallback
        """
        if explicit_score is not None:
            return explicit_score

        if self.auto_classify:
            return auto_classify_significance(
                content,
                ollama_host=self.ollama_host,
                model=self.ollama_model
            )

        return default_score

    def _generate_doc_id(self, content: str, source: str) -> str:
        """Generate stable document ID from content hash."""
        hash_input = f"{source}:{content[:500]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def load_importance_index(self, index_path: str) -> Dict[str, float]:
        """
        Load the importance index from the parsed transfer packets.

        The importance index maps document identifiers to their
        experiential significance scores (0-10).
        """
        importance_map = {}

        try:
            with open(index_path, 'r') as f:
                content = f.read()

            current_score = 0
            for line in content.split('\n'):
                line = line.strip()

                # Parse score headers
                if line.startswith('## Importance Score:'):
                    try:
                        score_str = line.replace('## Importance Score:', '').replace('/10', '').strip()
                        current_score = int(score_str)
                    except ValueError:
                        pass

                # Parse packet references
                elif line.startswith('- **['):
                    # Extract packet name
                    start = line.find('[') + 1
                    end = line.find(']')
                    if start > 0 and end > start:
                        packet_name = line[start:end]
                        importance_map[packet_name] = current_score

        except FileNotFoundError:
            pass

        self._importance_index = importance_map
        return importance_map

    def get_importance_score(self, doc_title: str, default: float = 5.0) -> float:
        """Look up importance score for a document."""
        # Try exact match
        if doc_title in self._importance_index:
            return float(self._importance_index[doc_title])

        # Try partial match
        for key, score in self._importance_index.items():
            if key in doc_title or doc_title in key:
                return float(score)

        return default

    def ingest_transfer_packets(self, packets_dir: str) -> int:
        """
        Ingest all transfer packets from the parsed corpus.

        Each packet becomes a document in the Ur-Codex with its
        importance score from the index.
        """
        packets_path = Path(packets_dir) / "packets"
        if not packets_path.exists():
            return 0

        # Load importance index
        index_path = Path(packets_dir) / "04_IMPORTANCE_INDEX.md"
        if index_path.exists():
            self.load_importance_index(str(index_path))

        ingested = 0
        for packet_file in packets_path.glob("*.md"):
            with open(packet_file, 'r') as f:
                content = f.read()

            # Extract title from first line
            lines = content.split('\n')
            title = lines[0].strip('#').strip() if lines else packet_file.stem

            # Get importance score
            importance = self.get_importance_score(title)

            # Create document
            doc_id = self._generate_doc_id(content, str(packet_file))

            # Add to collection
            self.collection.upsert(
                ids=[doc_id],
                documents=[content],
                metadatas=[{
                    "source_file": str(packet_file),
                    "doc_type": "transfer_packet",
                    "title": title,
                    "importance_score": importance,
                    "ingested_at": datetime.now().isoformat()
                }]
            )
            ingested += 1

        return ingested

    def ingest_psychological_profiles(self, profiles_dir: str) -> int:
        """
        Ingest psychological assessment documents.

        These are high-importance documents that define the cognitive
        fingerprint and should be weighted accordingly.
        """
        profiles_path = Path(profiles_dir)
        if not profiles_path.exists():
            return 0

        ingested = 0
        for profile_file in profiles_path.glob("*.md"):
            with open(profile_file, 'r') as f:
                content = f.read()

            title = profile_file.stem
            doc_id = self._generate_doc_id(content, str(profile_file))

            # Psychological profiles are inherently high-importance (8-10)
            importance = 9.0

            self.collection.upsert(
                ids=[doc_id],
                documents=[content],
                metadatas=[{
                    "source_file": str(profile_file),
                    "doc_type": "psychological",
                    "title": title,
                    "importance_score": importance,
                    "ingested_at": datetime.now().isoformat()
                }]
            )
            ingested += 1

        return ingested

    def ingest_cognitive_fingerprint(self, fingerprint_path: str) -> bool:
        """
        Ingest the master cognitive fingerprint.

        This is the single most important document in the Ur-Codex—
        it defines who Michael is for voice replication and
        Russellian calibration.
        """
        path = Path(fingerprint_path)
        if not path.exists():
            return False

        with open(path, 'r') as f:
            content = f.read()

        doc_id = self._generate_doc_id(content, str(path))

        # Maximum importance
        self.collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                "source_file": str(path),
                "doc_type": "cognitive_fingerprint",
                "title": "MICHAEL_COGNITIVE_FINGERPRINT",
                "importance_score": 10.0,
                "ingested_at": datetime.now().isoformat()
            }]
        )

        return True

    def ingest_creative_corpus(self, creative_dir: str) -> int:
        """
        Ingest creative writing samples.

        Creative work reveals voice, concerns, and authentic expression.
        Generally high importance for voice calibration.
        """
        creative_path = Path(creative_dir)
        if not creative_path.exists():
            return 0

        ingested = 0
        for creative_file in creative_path.glob("**/*.md"):
            with open(creative_file, 'r') as f:
                content = f.read()

            title = creative_file.stem
            doc_id = self._generate_doc_id(content, str(creative_file))

            # Creative work is important for voice calibration
            importance = 7.0

            self.collection.upsert(
                ids=[doc_id],
                documents=[content],
                metadatas=[{
                    "source_file": str(creative_file),
                    "doc_type": "creative",
                    "title": title,
                    "importance_score": importance,
                    "ingested_at": datetime.now().isoformat()
                }]
            )
            ingested += 1

        return ingested

    def ingest_conversations(self, conversations_dir: str, chunk_size: int = 2000) -> int:
        """
        Ingest conversation archive from parsed OpenAI conversations.

        These are the 290K+ lines of conversational data that form the
        behavioral corpus for understanding Michael's communication patterns.

        Large conversations are chunked to fit embedding limits while
        preserving context through overlap.
        """
        conv_path = Path(conversations_dir)
        if not conv_path.exists():
            return 0

        ingested = 0

        for conv_file in conv_path.glob("*.md"):
            try:
                with open(conv_file, 'r') as f:
                    content = f.read()

                # Parse YAML frontmatter for metadata
                metadata = {
                    "source_file": str(conv_file),
                    "doc_type": "conversation",
                    "importance_score": 6.0,  # Conversations are contextually important
                    "ingested_at": datetime.now().isoformat()
                }

                # Extract metadata from frontmatter if present
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        content_body = parts[2]

                        # Extract key fields from frontmatter
                        for line in frontmatter.split('\n'):
                            if line.startswith('conversation_id:'):
                                metadata['conversation_id'] = line.split(':', 1)[1].strip()
                            elif line.startswith('primary_topics:'):
                                metadata['topics'] = line.split(':', 1)[1].strip()
                            elif line.startswith('conversation_type:'):
                                metadata['conversation_type'] = line.split(':', 1)[1].strip()
                            elif line.startswith('michael_voice_strength:'):
                                strength = line.split(':', 1)[1].strip().lower()
                                # Boost importance for high voice strength
                                if strength == 'high':
                                    metadata['importance_score'] = 7.0
                                elif strength == 'very_high':
                                    metadata['importance_score'] = 8.0

                        content = content_body

                # Chunk large conversations
                if len(content) > chunk_size:
                    chunks = []
                    words = content.split()
                    current_chunk = []
                    current_size = 0

                    for word in words:
                        current_chunk.append(word)
                        current_size += len(word) + 1
                        if current_size >= chunk_size:
                            chunks.append(' '.join(current_chunk))
                            # Keep last 50 words for overlap
                            current_chunk = current_chunk[-50:]
                            current_size = sum(len(w) + 1 for w in current_chunk)

                    if current_chunk:
                        chunks.append(' '.join(current_chunk))

                    # Ingest each chunk
                    for i, chunk in enumerate(chunks):
                        chunk_id = self._generate_doc_id(chunk, f"{conv_file}_chunk_{i}")
                        chunk_metadata = metadata.copy()
                        chunk_metadata['chunk_index'] = i
                        chunk_metadata['total_chunks'] = len(chunks)

                        self.collection.upsert(
                            ids=[chunk_id],
                            documents=[chunk],
                            metadatas=[chunk_metadata]
                        )
                else:
                    doc_id = self._generate_doc_id(content, str(conv_file))
                    self.collection.upsert(
                        ids=[doc_id],
                        documents=[content],
                        metadatas=[metadata]
                    )

                ingested += 1

                # Log progress every 100 conversations
                if ingested % 100 == 0:
                    print(f"Ingested {ingested} conversations...")

            except Exception as e:
                print(f"Error ingesting conversation {conv_file}: {e}")
                continue

        return ingested

    def ingest_complete_corpus(self, corpus_root: str) -> Dict[str, int]:
        """
        Ingest the entire Complete Corpus.

        This is the full Ur-Codex ingestion that loads all document types
        with appropriate importance scoring.
        """
        corpus_path = Path(corpus_root)
        results = {
            "transfer_packets": 0,
            "psychological": 0,
            "creative": 0,
            "conversations": 0,
            "fingerprint": False
        }

        # Transfer packets
        packets_dir = corpus_path / "parsed_transfer_packets"
        if packets_dir.exists():
            results["transfer_packets"] = self.ingest_transfer_packets(str(packets_dir))

        # Psychological assessments
        psych_dir = corpus_path / "parsed_psychological_assessments"
        if psych_dir.exists():
            results["psychological"] = self.ingest_psychological_profiles(str(psych_dir))

        # Creative writing
        creative_dir = corpus_path / "parsed_creative_writing"
        if creative_dir.exists():
            results["creative"] = self.ingest_creative_corpus(str(creative_dir))

        # Conversation archive (290K+ lines of behavioral data)
        conversations_dir = corpus_path / "parsed_openai_archive" / "conversations"
        if conversations_dir.exists():
            print("Ingesting conversation archive (this may take a while)...")
            results["conversations"] = self.ingest_conversations(str(conversations_dir))

        # Cognitive fingerprint
        fingerprint_path = corpus_path / "MICHAEL_COGNITIVE_FINGERPRINT.md"
        if fingerprint_path.exists():
            results["fingerprint"] = self.ingest_cognitive_fingerprint(str(fingerprint_path))

        # Also ingest the training guide and validation docs
        for doc_name in ["DOLPHIN_TRAINING_GUIDE.md", "VOICE_VALIDATION.md"]:
            doc_path = corpus_path / doc_name
            if doc_path.exists():
                with open(doc_path, 'r') as f:
                    content = f.read()

                doc_id = self._generate_doc_id(content, str(doc_path))
                self.collection.upsert(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[{
                        "source_file": str(doc_path),
                        "doc_type": "voice_calibration",
                        "title": doc_name.replace('.md', ''),
                        "importance_score": 9.0,
                        "ingested_at": datetime.now().isoformat()
                    }]
                )

        return results

    def query(
        self,
        query_text: str,
        n_results: int = 20,
        doc_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Query the Ur-Codex for relevant documents.

        Returns documents with similarity scores and metadata
        for Sophimatic weighting.
        """
        where_filter = None
        if doc_types:
            where_filter = {"doc_type": {"$in": doc_types}}

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        documents = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else 0.5

                # Convert distance to similarity (cosine distance -> similarity)
                similarity = 1 - distance

                documents.append({
                    'content': doc,
                    'id': results['ids'][0][i] if results['ids'] else str(i),
                    'metadata': metadata,
                    'similarity': similarity
                })

        return documents

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the Ur-Codex."""
        count = self.collection.count()

        # Sample to get doc type distribution
        # Use try-except to handle ChromaDB version compatibility issues with peek()
        doc_types = {}
        try:
            sample = self.collection.peek(limit=min(100, count))
            if sample['metadatas']:
                for meta in sample['metadatas']:
                    doc_type = meta.get('doc_type', 'unknown')
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        except (AttributeError, KeyError, Exception) as e:
            # ChromaDB version mismatch - peek() fails on old data format
            # Fall back to just returning count without distribution
            doc_types = {"note": f"distribution unavailable ({type(e).__name__})"}

        return {
            "total_documents": count,
            "doc_type_distribution": doc_types,
            "importance_index_size": len(self._importance_index)
        }

    def add_conversation(
        self,
        content: str,
        importance_score: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a new conversation exchange to the Ur-Codex.

        This allows the corpus to grow over time as new
        significant exchanges occur.

        Args:
            content: The conversation text to add
            importance_score: Explicit score (1-10). If None, auto-classifies.
            metadata: Additional metadata to attach

        Returns:
            doc_id: The generated document ID
        """
        doc_id = self._generate_doc_id(content, f"conversation:{datetime.now().isoformat()}")

        # Auto-classify if no explicit score provided
        score = self._get_importance_score(content, importance_score, default_score=5.0)

        doc_metadata = {
            "source_file": "live_conversation",
            "doc_type": "conversation",
            "title": f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "importance_score": score,
            "auto_classified": importance_score is None,
            "ingested_at": datetime.now().isoformat()
        }

        if metadata:
            doc_metadata.update(metadata)

        self.collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[doc_metadata]
        )

        return doc_id
