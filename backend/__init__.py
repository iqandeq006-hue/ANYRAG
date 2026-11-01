"""
AnyRAG - Universal Document Ingestion, Retrieval, Persona & Comparison Engine.
"""

from backend.engine import AnyRAG
from backend.storage.vector_store import VectorStore
from backend.storage.bm25 import BM25Index
from backend.agents.llm_client import (
    LLMClient,
    LLMError,
    LLMConnectionError,
    LLMGenerationError,
)
from backend.agents.llama_server import LlamaServerManager
from backend.agents.persona import DocumentPersona
from backend.agents.comparator import DocumentComparator
from backend.agents.debate import DebateSession
from backend.parsers.registry import parse_document
from backend.chunking.chunker import RecursiveChunker
from backend.embeddings.embedder import LocalEmbedder, get_embedder

__version__ = "0.1.0"

__all__ = [
    "AnyRAG",
    "VectorStore",
    "BM25Index",
    "LLMClient",
    "LLMError",
    "LLMConnectionError",
    "LLMGenerationError",
    "LlamaServerManager",
    "DocumentPersona",
    "DocumentComparator",
    "DebateSession",
    "parse_document",
    "RecursiveChunker",
    "LocalEmbedder",
    "get_embedder",
    "__version__",
]

