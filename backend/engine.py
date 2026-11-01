import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from backend.config import DEFAULT_DB_PATH, DEFAULT_CHROMA_DIR, DEFAULT_MODEL_DIR
from backend.parsers.registry import parse_document
from backend.chunking.chunker import RecursiveChunker
from backend.embeddings.embedder import get_embedder
from backend.storage.vector_store import VectorStore
from backend.agents.persona import DocumentPersona
from backend.agents.comparator import DocumentComparator
from backend.agents.llm_client import LLMClient

logger = logging.getLogger("anyrag.engine")

class AnyRAG:
    """
    Main entry point and coordinator for the AnyRAG system.
    """

    def __init__(self, db_path: Optional[str | Path] = None, model_path: Optional[str | Path] = None, llm_client: Optional[LLMClient] = None):
        self.vector_store = VectorStore(db_path or DEFAULT_CHROMA_DIR)
        self._model_path = model_path
        self._embedder = None
        self.chunker = RecursiveChunker()
        self.llm = llm_client or LLMClient()

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = get_embedder(self._model_path or DEFAULT_MODEL_DIR)
        return self._embedder

    def ingest(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Ingests and indexes a single document (PDF, DOCX, PPTX, Markdown, Text, etc.).
        Extracts content, generates chunks and embeddings, and persists to vector storage.
        """
        path = Path(file_path).resolve()
        logger.info(f"Parsing document: {path.name}...")
        extracted_doc = parse_document(path)

        logger.info(f"Chunking {len(extracted_doc.sections)} sections...")
        chunks = self.chunker.chunk_document(extracted_doc)
        if not chunks:
            logger.warning(f"No text chunks extracted from {path.name}.")
            return {"status": "empty", "doc_id": extracted_doc.doc_id, "chunk_count": 0}

        logger.info(f"Generating embeddings for {len(chunks)} chunks using local model...")
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedder.embed_texts(chunk_texts)

        logger.info("Storing in vector database...")
        self.vector_store.add_document_and_chunks(extracted_doc, chunks, embeddings)
        logger.info(f"Successfully indexed: {extracted_doc.file_name} ({len(chunks)} chunks, ID: {extracted_doc.doc_id})")

        return {
            "status": "success",
            "doc_id": extracted_doc.doc_id,
            "file_name": extracted_doc.file_name,
            "file_type": extracted_doc.file_type,
            "chunk_count": len(chunks)
        }

    def purge(self, doc_id_or_path: str) -> int:
        """Cascade deletes a document and all its embedded chunks from the vector database."""
        deleted_count = self.vector_store.purge_document(doc_id_or_path)
        logger.info(f"Purged document '{doc_id_or_path}'. Cascade deleted {deleted_count} chunks.")
        return deleted_count

    def clear(self):
        """Purges all documents from the system."""
        self.vector_store.clear_all()
        logger.info("All documents and vectors have been cleared.")

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents."""
        return self.vector_store.list_documents()

    def get_persona(self, doc_id_or_name: str) -> DocumentPersona:
        """Instantiate a grounded conversational persona for a document."""
        # Resolve doc_id if file name was passed
        docs = self.list_documents()
        target_id = doc_id_or_name
        for d in docs:
            if d["doc_id"] == doc_id_or_name or d["file_name"] == doc_id_or_name or d["file_path"] == doc_id_or_name:
                target_id = d["doc_id"]
                break
        return DocumentPersona(target_id, self.vector_store, llm_client=self.llm)

    def ask(self, doc_id_or_name: str, query: str, top_k: int = 4) -> Dict[str, Any]:
        """Ask a question to a specific document persona ('Doc Jarvis')."""
        persona = self.get_persona(doc_id_or_name)
        return persona.ask(query, top_k=top_k)

    def compare(self, doc1: str, doc2: str, query: Optional[str] = None) -> Dict[str, Any]:
        """Compare two documents with query-driven cross-retrieval."""
        persona1 = self.get_persona(doc1)
        persona2 = self.get_persona(doc2)
        comparator = DocumentComparator(persona1.doc_id, persona2.doc_id, self.vector_store, llm_client=self.llm)
        if query:
            return comparator.compare_query(query)
        return comparator.compare_query()

    def semantic_diff(self, doc1: str, doc2: str) -> Dict[str, Any]:
        """Perform chunk-level semantic difference analysis between two documents."""
        persona1 = self.get_persona(doc1)
        persona2 = self.get_persona(doc2)
        comparator = DocumentComparator(persona1.doc_id, persona2.doc_id, self.vector_store, llm_client=self.llm)
        return comparator.compute_semantic_diff()

    def search_all(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Global hybrid search (dense + BM25 keyword matching via RRF) across all indexed documents."""
        query_vec = self.embedder.embed_query(query)
        return self.vector_store.hybrid_search(query_text=query, query_vector=query_vec, top_k=top_k)
