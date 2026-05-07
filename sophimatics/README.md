# Sophimatics — Reference Implementation

These modules implement the architectural claims described in
*The Sovereign Prosthesis* paper. They are the working proof of
concept referenced in the IACAP 2026 presentation.

## Modules

**ur_codex.py** — `UrCodexManager`  
Longitudinal corpus management using ChromaDB. Handles ingestion,
chunking, and retrieval of the user's conversational history and
knowledge base. This is the Ur-Codex described in Section 2.

**temporal_weighting.py** — `TemporalWeightingEngine`  
Two-dimensional temporal weighting: alpha=0.6 (experiential
significance) + beta=0.4 (chronological recency). Implements the
Sophimatic temporal manifold described in Section 3.

**russellian_os.py** — `RussellianOS`  
Dissent calibration engine. Five-level `DissentLevel` enum, domain
detection, trigger pattern recognition. Implements the Russellian
OS described in Section 4.

**state_awareness.py** — `StateAwarenessEngine`  
Persistent project tracking, recurring concern detection, logical
vacancy identification. The operational criterion for proximal
integration described in Section 3.

**wiki_integration.py** — `WikiSophimaticsEngine`  
Wiki corpus integration with Sophimatics metadata: importance
scores, temporal status, disposition classification. Connects
the Karpathy wiki architecture to the temporal weighting engine.

## Stack

- Python 3.9+
- ChromaDB (vector store)
- FastAPI (API layer)
- Ollama (local inference)

## Quick Start

```bash
pip install chromadb fastapi uvicorn
```

```python
from sophimatics import UrCodexManager, TemporalWeightingEngine, RussellianOS

# Ingest a document into the longitudinal corpus
codex = UrCodexManager(persist_directory="./my_codex")
from sophimatics.ur_codex import CodexEntry
entry = CodexEntry(content="Your text here.", source="conversation")
codex.ingest(entry)

# Score memories on the temporal manifold
engine = TemporalWeightingEngine()  # alpha=0.6, beta=0.4

# Check for epistemic patterns requiring dissent
os = RussellianOS()
signal = os.analyse("Everyone knows AGI is five years away.", domain="empirical")
if signal:
    print(os.posture(signal.level))
```

## Citation

```bibtex
@inproceedings{bouchard2026sovereign,
  title     = {The Sovereign Prosthesis: Toward a Functional Sophimatics of Cognitive Extension},
  author    = {Bouchard, Michael},
  booktitle = {Proceedings of IACAP 2026},
  year      = {2026},
  doi       = {10.5281/zenodo.19375039},
  note      = {University of Kansas, July 15--17, 2026}
}
```
