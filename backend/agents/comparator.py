from typing import List, Dict, Any, Optional
import numpy as np
from backend.storage.vector_store import VectorStore
from backend.embeddings.embedder import get_embedder
from .llm_client import LLMClient
from .persona import DocumentPersona


class DocumentComparator:
    """
    Engine for comparing two documents using:
    1. Dual-Persona interrogation (talking to both document agents).
    2. Cross-retrieval comparative synthesis (RAG compare & contrast).
    3. Chunk-level Semantic Diff (divergence and redundancy analysis).

    Supports both same-document/shared-store and cross-document/dual-store modes.
    """

    def __init__(
        self,
        doc1_id: str,
        doc2_id: str,
        vector_store: VectorStore,
        vector_store_2: Optional[VectorStore] = None,
        llm_client: Optional[LLMClient] = None
    ):
        self.doc1_id = doc1_id
        self.doc2_id = doc2_id
        self.vector_store_1 = vector_store
        self.vector_store_2 = vector_store_2 or vector_store
        self.llm = llm_client or LLMClient()
        self.embedder = get_embedder()

        # Initialize the two distinct document personas using their respective stores
        self.persona1 = DocumentPersona(doc1_id, self.vector_store_1, llm_client=self.llm)
        self.persona2 = DocumentPersona(doc2_id, self.vector_store_2, llm_client=self.llm)

    def compare_query(
        self,
        query: str = "Compare the main themes, differences, and key arguments between both documents",
        top_k_per_doc: int = 4
    ) -> Dict[str, Any]:
        """Query-driven comparison across both documents with isolated store querying."""
        query_vec = self.embedder.embed_query(query)

        # Retrieve top chunks from Doc 1 via Store 1
        chunks_doc1 = self.vector_store_1.hybrid_search(
            query_text=query,
            query_vector=query_vec,
            top_k=top_k_per_doc,
            doc_ids=[self.doc1_id]
        )

        # Retrieve top chunks from Doc 2 via Store 2
        chunks_doc2 = self.vector_store_2.hybrid_search(
            query_text=query,
            query_vector=query_vec,
            top_k=top_k_per_doc,
            doc_ids=[self.doc2_id]
        )

        # Build comparison system prompt
        system_prompt = (
            "You are an expert analytical intelligence comparing two distinct documents.\n"
            "Analyze the provided excerpts from Document 1 and Document 2.\n"
            "Structure your answer with:\n"
            "1. Core Similarities\n"
            "2. Notable Differences / Divergences\n"
            "3. Unique Takeaways from Document 1\n"
            "4. Unique Takeaways from Document 2\n"
            "5. Executive Summary\n"
            "Keep it concise, objective, and grounded directly in the text."
        )

        user_prompt = (
            f"User Comparison Request: {query}\n\n"
            f"=== DOCUMENT 1: {self.persona1.doc_name} ===\n"
            + "\n---\n".join(f"[{c.get('section_title') or 'Section'}]: {c['content']}" for c in chunks_doc1)
            + f"\n\n=== DOCUMENT 2: {self.persona2.doc_name} ===\n"
            + "\n---\n".join(f"[{c.get('section_title') or 'Section'}]: {c['content']}" for c in chunks_doc2)
        )

        combined_chunks = chunks_doc1 + chunks_doc2
        comparison_result = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context_chunks=combined_chunks
        )

        return {
            "doc1_name": self.persona1.doc_name,
            "doc2_name": self.persona2.doc_name,
            "query": query,
            "comparison": comparison_result,
            "doc1_chunks": chunks_doc1,
            "doc2_chunks": chunks_doc2
        }

    def compute_semantic_diff(
        self,
        similarity_threshold_high: float = 0.70,
        similarity_threshold_low: float = 0.40
    ) -> Dict[str, Any]:
        """
        Computes chunk-to-chunk cosine similarities to find semantic divergence and convergence.
        Correctly queries chunks from vector_store_1 for doc1 and vector_store_2 for doc2.
        """
        chunks_1 = self.vector_store_1.get_all_chunks_for_doc(self.doc1_id)
        chunks_2 = self.vector_store_2.get_all_chunks_for_doc(self.doc2_id)

        if not chunks_1 or not chunks_2:
            return {
                "error": "One or both documents have no chunks.",
                "doc1_chunks_found": len(chunks_1) if chunks_1 else 0,
                "doc2_chunks_found": len(chunks_2) if chunks_2 else 0,
            }

        # Vectorized cosine similarity matrix: len(chunks_1) x len(chunks_2)
        v1 = np.vstack([c["vector"] for c in chunks_1]).astype(np.float32)  # shape (N, D)
        v2 = np.vstack([c["vector"] for c in chunks_2]).astype(np.float32)  # shape (M, D)

        norm1 = np.linalg.norm(v1, axis=1, keepdims=True)
        norm2 = np.linalg.norm(v2, axis=1, keepdims=True)
        norm1[norm1 == 0] = 1e-10
        norm2[norm2 == 0] = 1e-10
        sim_matrix = np.matmul(v1 / norm1, (v2 / norm2).T)  # shape (N, M) via BLAS

        # For each chunk in doc 1, best match in doc 2
        max_for_1 = sim_matrix.max(axis=1) if sim_matrix.size > 0 else np.array([])
        # For each chunk in doc 2, best match in doc 1
        max_for_2 = sim_matrix.max(axis=0) if sim_matrix.size > 0 else np.array([])

        common_topics = []
        unique_to_doc1 = []
        unique_to_doc2 = []

        # Find overlaps and unique sections
        for idx, score in enumerate(max_for_1):
            chunk = chunks_1[idx]
            best_match_idx = int(np.argmax(sim_matrix[idx]))
            best_chunk_2 = chunks_2[best_match_idx]

            if score >= similarity_threshold_high:
                common_topics.append({
                    "similarity": round(float(score), 3),
                    "doc1_section": chunk.get("section_title") or f"Chunk {idx+1}",
                    "doc1_content": chunk["content"][:200] + "...",
                    "doc2_section": best_chunk_2.get("section_title") or f"Chunk {best_match_idx+1}",
                    "doc2_content": best_chunk_2["content"][:200] + "..."
                })
            elif score <= similarity_threshold_low:
                unique_to_doc1.append({
                    "max_similarity": round(float(score), 3),
                    "section": chunk.get("section_title") or f"Chunk {idx+1}",
                    "content": chunk["content"][:200] + "..."
                })

        for idx, score in enumerate(max_for_2):
            if score <= similarity_threshold_low:
                chunk = chunks_2[idx]
                unique_to_doc2.append({
                    "max_similarity": round(float(score), 3),
                    "section": chunk.get("section_title") or f"Chunk {idx+1}",
                    "content": chunk["content"][:200] + "..."
                })

        overall_similarity = float(np.mean(sim_matrix)) if sim_matrix.size > 0 else 0.0

        return {
            "doc1_name": self.persona1.doc_name,
            "doc2_name": self.persona2.doc_name,
            "overall_semantic_similarity": round(overall_similarity, 3),
            "common_topics_count": len(common_topics),
            "unique_doc1_count": len(unique_to_doc1),
            "unique_doc2_count": len(unique_to_doc2),
            "common_samples": common_topics[:3],
            "unique_doc1_samples": unique_to_doc1[:3],
            "unique_doc2_samples": unique_to_doc2[:3]
        }
