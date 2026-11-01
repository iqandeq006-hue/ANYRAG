import math
import pickle
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional, Any

class BM25Index:
    """
    High-performance, pure-Python BM25Okapi sparse retrieval index.
    Zero external dependencies. Provides exact keyword matching for IDs, codes,
    acronyms, and exact terms to complement dense vector embeddings.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_len: Dict[str, int] = {}  # chunk_id -> length in tokens
        self.doc_ids: List[str] = []       # chunk_ids
        self.doc_map: Dict[str, str] = {}  # chunk_id -> raw text
        self.chunk_to_doc_id: Dict[str, str] = {}  # chunk_id -> parent doc_id
        self.inverted_index: Dict[str, List[Tuple[str, int]]] = defaultdict(list)  # term -> [(chunk_id, freq)]
        self.doc_frequencies: Counter = Counter()  # term -> count of docs containing term
        self.avg_doc_len: float = 0.0
        self.total_docs: int = 0
        self.tokenizer = re.compile(r"\w+", re.UNICODE)

    def _tokenize(self, text: str) -> List[str]:
        """Normalize text into lowercase alphanumeric tokens."""
        if not text:
            return []
        return self.tokenizer.findall(text.lower())

    def add_chunk(self, chunk_id: str, text: str, doc_id: str = ""):
        """Add or update a single chunk in the sparse index."""
        # Remove existing if already present
        if chunk_id in self.doc_len:
            self.remove_chunk(chunk_id)

        tokens = self._tokenize(text)
        length = len(tokens)
        self.doc_len[chunk_id] = length
        self.doc_ids.append(chunk_id)
        self.doc_map[chunk_id] = text
        self.chunk_to_doc_id[chunk_id] = doc_id

        term_counts = Counter(tokens)
        for term, freq in term_counts.items():
            self.inverted_index[term].append((chunk_id, freq))
            self.doc_frequencies[term] += 1

        self.total_docs = len(self.doc_ids)
        total_len = sum(self.doc_len.values())
        self.avg_doc_len = total_len / self.total_docs if self.total_docs > 0 else 0.0

    def add_chunks_batch(self, chunks: List[Tuple[str, str, str]]):
        """Batch add chunks: list of (chunk_id, text, doc_id)."""
        for chunk_id, text, doc_id in chunks:
            self.add_chunk(chunk_id, text, doc_id)

    def remove_chunk(self, chunk_id: str):
        """Remove a specific chunk from the sparse index."""
        if chunk_id not in self.doc_len:
            return

        text = self.doc_map.get(chunk_id, "")
        tokens = self._tokenize(text)
        unique_terms = set(tokens)

        for term in unique_terms:
            self.doc_frequencies[term] -= 1
            if self.doc_frequencies[term] <= 0:
                del self.doc_frequencies[term]
            if term in self.inverted_index:
                self.inverted_index[term] = [
                    (cid, f) for cid, f in self.inverted_index[term] if cid != chunk_id
                ]
                if not self.inverted_index[term]:
                    del self.inverted_index[term]

        del self.doc_len[chunk_id]
        if chunk_id in self.doc_map:
            del self.doc_map[chunk_id]
        if chunk_id in self.chunk_to_doc_id:
            del self.chunk_to_doc_id[chunk_id]
        if chunk_id in self.doc_ids:
            self.doc_ids.remove(chunk_id)

        self.total_docs = len(self.doc_ids)
        total_len = sum(self.doc_len.values())
        self.avg_doc_len = total_len / self.total_docs if self.total_docs > 0 else 0.0

    def remove_document_chunks(self, doc_id: str) -> int:
        """Remove all chunks belonging to a parent doc_id."""
        matching_chunk_ids = [
            cid for cid, parent_id in self.chunk_to_doc_id.items() if parent_id == doc_id
        ]
        for cid in matching_chunk_ids:
            self.remove_chunk(cid)
        return len(matching_chunk_ids)

    def clear(self):
        """Reset the BM25 index completely."""
        self.doc_len.clear()
        self.doc_ids.clear()
        self.doc_map.clear()
        self.chunk_to_doc_id.clear()
        self.inverted_index.clear()
        self.doc_frequencies.clear()
        self.avg_doc_len = 0.0
        self.total_docs = 0

    def save(self, file_path: str | Path):
        """Persist BM25 index state to disk atomically."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "version": 1,
            "k1": self.k1,
            "b": self.b,
            "doc_len": self.doc_len,
            "doc_ids": self.doc_ids,
            "doc_map": self.doc_map,
            "chunk_to_doc_id": self.chunk_to_doc_id,
            "inverted_index": dict(self.inverted_index),
            "doc_frequencies": dict(self.doc_frequencies),
            "avg_doc_len": self.avg_doc_len,
            "total_docs": self.total_docs,
        }
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "wb") as f:
            pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
        temp_path.replace(path)

    def load(self, file_path: str | Path) -> bool:
        """Load BM25 index state from disk. Returns True if successfully loaded."""
        path = Path(file_path)
        if not path.exists():
            return False
        try:
            with open(path, "rb") as f:
                state = pickle.load(f)
            if not isinstance(state, dict) or state.get("version") != 1:
                return False
            self.k1 = state["k1"]
            self.b = state["b"]
            self.doc_len = state["doc_len"]
            self.doc_ids = state["doc_ids"]
            self.doc_map = state["doc_map"]
            self.chunk_to_doc_id = state["chunk_to_doc_id"]
            self.inverted_index = defaultdict(list, state["inverted_index"])
            self.doc_frequencies = Counter(state["doc_frequencies"])
            self.avg_doc_len = state["avg_doc_len"]
            self.total_docs = state["total_docs"]
            return True
        except Exception:
            return False

    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_ids: Optional[List[str]] = None
    ) -> List[Tuple[str, float]]:
        """
        Calculates BM25Okapi scores for the query against indexed chunks.
        Optionally filters to chunks belonging to specific parent document IDs.
        Returns sorted list of (chunk_id, score) in descending order.
        """
        if self.total_docs == 0:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        allowed_parent_ids = set(doc_ids) if doc_ids else None
        scores: Dict[str, float] = defaultdict(float)

        for token in query_tokens:
            if token not in self.inverted_index:
                continue

            # Robertson-Spärck Jones IDF with floor protection
            df = self.doc_frequencies[token]
            idf = math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))

            for chunk_id, freq in self.inverted_index[token]:
                if allowed_parent_ids and self.chunk_to_doc_id.get(chunk_id) not in allowed_parent_ids:
                    continue

                dl = self.doc_len[chunk_id]
                denominator = freq + self.k1 * (1.0 - self.b + self.b * (dl / (self.avg_doc_len or 1.0)))
                term_score = idf * (freq * (self.k1 + 1.0)) / denominator
                scores[chunk_id] += term_score

        if not scores:
            return []

        # Sort descending by BM25 score
        sorted_results = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return sorted_results[:top_k]
