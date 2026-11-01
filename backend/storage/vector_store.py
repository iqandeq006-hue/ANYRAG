import datetime
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import chromadb
from chromadb.config import Settings
from backend.config import DEFAULT_CHROMA_DIR, DEFAULT_DB_PATH
from backend.chunking.chunker import DocumentChunk
from backend.parsers.base import ExtractedDocument
from .bm25 import BM25Index

class VectorStore:
    """
    Production-grade Hybrid VectorStore backed by ChromaDB and BM25Okapi.
    Combines:
    1. Dense vector embeddings with HNSW cosine metric for deep semantic comprehension.
    2. Sparse BM25Okapi inverted index for exact keyword, ID, code, and term precision.
    3. Reciprocal Rank Fusion (RRF) for mathematically sound result merging.
    """

    def __init__(self, db_path: str | Path = DEFAULT_CHROMA_DIR):
        raw_path = Path(db_path)
        # If a file path like .db is provided, use a chromadb subdirectory beside it
        if raw_path.suffix:
            self.chroma_dir = raw_path.parent / "chromadb"
        else:
            self.chroma_dir = raw_path

        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        # Initialize persistent Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        # Chunks collection using HNSW cosine metric
        self.chunks_col = self.client.get_or_create_collection(
            name="anyrag_chunks",
            metadata={"hnsw:space": "cosine"}
        )

        # Document metadata collection
        self.docs_col = self.client.get_or_create_collection(
            name="anyrag_docs"
        )

        # Persistent BM25 sparse index
        self.bm25_path = self.chroma_dir / "bm25_index.pkl"
        self.bm25 = BM25Index()
        self._hydrate_bm25()

    def _hydrate_bm25(self):
        """Pre-populate the BM25 index with persisted cache or fallback to Chroma rebuild."""
        count = self.chunks_col.count()
        if count == 0:
            if self.bm25_path.exists():
                try:
                    self.bm25_path.unlink()
                except Exception:
                    pass
            return

        # O(1) instant startup if cache file exists and chunk count matches
        if self.bm25_path.exists():
            if self.bm25.load(self.bm25_path) and self.bm25.total_docs == count:
                return

        # Fallback rebuild from Chroma and write cache
        try:
            self.bm25.clear()
            stored = self.chunks_col.get(include=["documents", "metadatas"])
            if stored and stored["ids"]:
                for cid, doc_text, meta in zip(stored["ids"], stored["documents"], stored["metadatas"]):
                    self.bm25.add_chunk(cid, doc_text or "", meta.get("doc_id", ""))
            self.bm25.save(self.bm25_path)
        except Exception:
            pass

    def add_document_and_chunks(self, doc: ExtractedDocument, chunks: List[DocumentChunk], embeddings: np.ndarray):
        """Atomically stores or updates a document, chunks, and embeddings in ChromaDB & BM25."""
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks count ({len(chunks)}) does not match embeddings count ({len(embeddings)})")

        # Purge any existing versions of this document by doc_id or file_path to avoid stale duplicates
        self.purge_document(doc.doc_id)
        self.purge_document(doc.file_path)

        # 1. Store document-level metadata
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.docs_col.upsert(
            ids=[doc.doc_id],
            documents=[doc.file_name],
            metadatas=[{
                "doc_id": doc.doc_id,
                "file_path": str(doc.file_path),
                "file_name": doc.file_name,
                "file_type": doc.file_type,
                "file_size": int(doc.file_size),
                "chunk_count": len(chunks),
                "metadata_json": json.dumps(doc.metadata),
                "indexed_at": now_iso
            }]
        )

        # 2. Store chunks and embeddings in ChromaDB + index in BM25
        if chunks:
            chunk_ids = [c.chunk_id for c in chunks]
            chunk_texts = [c.content for c in chunks]
            chunk_metas = []
            for c in chunks:
                chunk_metas.append({
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "chunk_index": int(c.chunk_index),
                    "section_title": c.section_title or "",
                    "page_number": int(c.page_number) if c.page_number is not None else -1,
                    "section_type": c.section_type or "text",
                    "metadata_json": json.dumps(c.metadata)
                })
                # Add to BM25 index
                self.bm25.add_chunk(c.chunk_id, c.content, c.doc_id)

            chunk_vectors = embeddings.astype(np.float32).tolist()
            self.chunks_col.upsert(
                ids=chunk_ids,
                embeddings=chunk_vectors,
                documents=chunk_texts,
                metadatas=chunk_metas
            )
            # Persist updated BM25 index
            try:
                self.bm25.save(self.bm25_path)
            except Exception:
                pass

    def purge_document(self, doc_id_or_path: str) -> int:
        """
        Cascade delete: Removes the document and all associated chunk vectors from ChromaDB and BM25.
        Accepts doc_id, full file_path, or file_name.
        Returns the number of chunks purged.
        """
        target_doc_ids = set()

        # Check direct doc_id match
        existing = self.docs_col.get(ids=[doc_id_or_path])
        if existing and existing["ids"]:
            target_doc_ids.add(doc_id_or_path)

        # Check by file_path
        res_path = self.docs_col.get(where={"file_path": doc_id_or_path})
        if res_path and res_path["ids"]:
            target_doc_ids.update(res_path["ids"])

        # Check by file_name
        res_name = self.docs_col.get(where={"file_name": doc_id_or_path})
        if res_name and res_name["ids"]:
            target_doc_ids.update(res_name["ids"])

        if not target_doc_ids:
            return 0

        total_chunks = 0
        for doc_id in target_doc_ids:
            # Query all chunks belonging to doc_id
            chunks_data = self.chunks_col.get(where={"doc_id": doc_id})
            if chunks_data and chunks_data["ids"]:
                chunk_ids = chunks_data["ids"]
                total_chunks += len(chunk_ids)
                self.chunks_col.delete(ids=chunk_ids)

            self.docs_col.delete(ids=[doc_id])
            # Remove from BM25
            self.bm25.remove_document_chunks(doc_id)

        # Persist updated BM25 index
        try:
            self.bm25.save(self.bm25_path)
        except Exception:
            pass

        return total_chunks

    def clear_all(self):
        """Completely purges all documents and vectors from ChromaDB and BM25."""
        self.client.delete_collection("anyrag_chunks")
        self.client.delete_collection("anyrag_docs")
        self.chunks_col = self.client.get_or_create_collection(
            name="anyrag_chunks",
            metadata={"hnsw:space": "cosine"}
        )
        self.docs_col = self.client.get_or_create_collection(
            name="anyrag_docs"
        )
        self.bm25.clear()
        if self.bm25_path.exists():
            try:
                self.bm25_path.unlink()
            except Exception:
                pass

    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns metadata for all indexed documents."""
        docs = self.docs_col.get(include=["metadatas"])
        results = []
        if docs and docs["metadatas"]:
            for meta in docs["metadatas"]:
                results.append({
                    "doc_id": meta.get("doc_id", ""),
                    "file_path": meta.get("file_path", ""),
                    "file_name": meta.get("file_name", ""),
                    "file_type": meta.get("file_type", ""),
                    "file_size": meta.get("file_size", 0),
                    "chunk_count": meta.get("chunk_count", 0),
                    "indexed_at": meta.get("indexed_at", "")
                })

        results.sort(key=lambda d: d.get("indexed_at", ""), reverse=True)
        return results

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document details by doc_id."""
        res = self.docs_col.get(ids=[doc_id], include=["metadatas"])
        if res and res["metadatas"] and len(res["metadatas"]) > 0:
            return res["metadatas"][0]
        return None

    def similarity_search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        doc_ids: Optional[List[str]] = None,
        min_score: float = 0.0,
        query_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search, optionally upgrading to hybrid search if query_text is given.
        """
        if query_text:
            return self.hybrid_search(
                query_text=query_text,
                query_vector=query_vector,
                top_k=top_k,
                doc_ids=doc_ids,
                min_score=min_score
            )

        total_chunks = self.chunks_col.count()
        if total_chunks == 0:
            return []

        where_clause = None
        if doc_ids:
            if len(doc_ids) == 1:
                where_clause = {"doc_id": doc_ids[0]}
            elif len(doc_ids) > 1:
                where_clause = {"doc_id": {"$in": doc_ids}}

        n_results = min(top_k, total_chunks)
        query_embeddings = [query_vector.astype(np.float32).tolist()]

        try:
            query_res = self.chunks_col.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
        except Exception:
            return []

        results = []
        if query_res and query_res["ids"] and len(query_res["ids"]) > 0:
            ids = query_res["ids"][0]
            docs = query_res["documents"][0]
            metas = query_res["metadatas"][0]
            distances = query_res["distances"][0]

            for cid, cdoc, cmeta, cdist in zip(ids, docs, metas, distances):
                score = float(1.0 - cdist)
                if score >= min_score:
                    extra_meta = {}
                    if cmeta.get("metadata_json"):
                        try:
                            extra_meta = json.loads(cmeta["metadata_json"])
                        except Exception:
                            pass

                    results.append({
                        "chunk_id": cid,
                        "doc_id": cmeta.get("doc_id"),
                        "chunk_index": cmeta.get("chunk_index", 0),
                        "content": cdoc,
                        "section_title": cmeta.get("section_title") or None,
                        "page_number": cmeta.get("page_number") if cmeta.get("page_number", -1) != -1 else None,
                        "section_type": cmeta.get("section_type", "text"),
                        "score": score,
                        "metadata": extra_meta
                    })

        return results[:top_k]

    def hybrid_search(
        self,
        query_text: str,
        query_vector: np.ndarray,
        top_k: int = 5,
        doc_ids: Optional[List[str]] = None,
        min_score: float = 0.0,
        dense_weight: float = 1.0,
        bm25_weight: float = 1.0,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining Dense HNSW Cosine Similarity and Sparse BM25Okapi
        using Reciprocal Rank Fusion (RRF).
        Guarantees both deep conceptual matching and precise exact-keyword/ID recall.
        """
        total_chunks = self.chunks_col.count()
        if total_chunks == 0:
            return []

        candidates_k = min(max(top_k * 3, 20), total_chunks)

        # 1. Dense Search via ChromaDB
        where_clause = None
        if doc_ids:
            if len(doc_ids) == 1:
                where_clause = {"doc_id": doc_ids[0]}
            elif len(doc_ids) > 1:
                where_clause = {"doc_id": {"$in": doc_ids}}

        dense_ranked_ids: List[str] = []
        dense_scores_map: Dict[str, float] = {}

        try:
            dense_res = self.chunks_col.query(
                query_embeddings=[query_vector.astype(np.float32).tolist()],
                n_results=candidates_k,
                where=where_clause,
                include=["distances"]
            )
            if dense_res and dense_res["ids"] and dense_res["ids"][0]:
                dense_ranked_ids = dense_res["ids"][0]
                dists = dense_res["distances"][0]
                for cid, dist in zip(dense_ranked_ids, dists):
                    dense_scores_map[cid] = float(1.0 - dist)
        except Exception:
            pass

        # 2. Sparse Search via BM25Okapi
        bm25_hits = self.bm25.search(query=query_text, top_k=candidates_k, doc_ids=doc_ids)
        bm25_ranked_ids = [hit[0] for hit in bm25_hits]
        bm25_scores_map = {hit[0]: hit[1] for hit in bm25_hits}

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF score = sum(weight / (rrf_k + rank + 1))
        rrf_scores: Dict[str, float] = {}
        all_candidate_ids = set(dense_ranked_ids) | set(bm25_ranked_ids)

        for cid in all_candidate_ids:
            rrf_score = 0.0
            if cid in dense_ranked_ids:
                rank_dense = dense_ranked_ids.index(cid)
                rrf_score += dense_weight * (1.0 / (rrf_k + rank_dense + 1))
            if cid in bm25_ranked_ids:
                rank_bm25 = bm25_ranked_ids.index(cid)
                rrf_score += bm25_weight * (1.0 / (rrf_k + rank_bm25 + 1))
            rrf_scores[cid] = rrf_score

        # Sort candidate IDs by RRF score descending
        sorted_cids = sorted(all_candidate_ids, key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]
        if not sorted_cids:
            return []

        # 4. Fetch metadata & documents for top candidates
        fetched = self.chunks_col.get(ids=sorted_cids, include=["documents", "metadatas"])
        chunks_by_id = {}
        if fetched and fetched["ids"]:
            for cid, cdoc, cmeta in zip(fetched["ids"], fetched["documents"], fetched["metadatas"]):
                extra_meta = {}
                if cmeta.get("metadata_json"):
                    try:
                        extra_meta = json.loads(cmeta["metadata_json"])
                    except Exception:
                        pass

                chunks_by_id[cid] = {
                    "chunk_id": cid,
                    "doc_id": cmeta.get("doc_id"),
                    "chunk_index": cmeta.get("chunk_index", 0),
                    "content": cdoc,
                    "section_title": cmeta.get("section_title") or None,
                    "page_number": cmeta.get("page_number") if cmeta.get("page_number", -1) != -1 else None,
                    "section_type": cmeta.get("section_type", "text"),
                    "score": round(rrf_scores[cid], 4),
                    "metadata": dict(
                        extra_meta,
                        retrieval="hybrid_rrf",
                        dense_score=round(dense_scores_map.get(cid, 0.0), 4),
                        bm25_score=round(bm25_scores_map.get(cid, 0.0), 4)
                    )
                }

        # Preserve sorted order
        results = [chunks_by_id[cid] for cid in sorted_cids if cid in chunks_by_id]
        return results

    def get_all_chunks_for_doc(self, doc_id: str) -> List[Dict[str, Any]]:
        """Retrieve all chunks and vectors for a document (used for DocumentComparator semantic diffs)."""
        res = self.chunks_col.get(
            where={"doc_id": doc_id},
            include=["documents", "metadatas", "embeddings"]
        )

        results = []
        if res and res["ids"]:
            ids = res["ids"]
            docs = res["documents"]
            metas = res["metadatas"]
            embeddings = res.get("embeddings", [])

            for idx, cid in enumerate(ids):
                cmeta = metas[idx]
                cdoc = docs[idx]
                cemb = embeddings[idx] if idx < len(embeddings) else None
                vec = np.array(cemb, dtype=np.float32) if cemb is not None else np.array([], dtype=np.float32)

                results.append({
                    "chunk_id": cid,
                    "doc_id": cmeta.get("doc_id"),
                    "chunk_index": cmeta.get("chunk_index", 0),
                    "content": cdoc,
                    "section_title": cmeta.get("section_title") or None,
                    "page_number": cmeta.get("page_number") if cmeta.get("page_number", -1) != -1 else None,
                    "vector": vec
                })

            results.sort(key=lambda x: x["chunk_index"])

        return results
