import logging
import os
import shutil
import sys
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from backend.agents.llm_client import (
    LLMClient,
    LLMError,
    LLMConnectionError,
    LLMGenerationError,
)
from backend.agents.llama_server import LlamaServerManager
from backend.storage.bm25 import BM25Index
from backend.storage.vector_store import VectorStore
from backend.parsers.base import ExtractedDocument, ExtractedSection
from backend.chunking.chunker import DocumentChunk


class TestLLMErrorHandling(unittest.TestCase):
    """Test that LLMClient raises typed exceptions and handles the OpenRouter -> Local fallback chain."""

    def test_openrouter_missing_key_raises_connection_error(self):
        client = LLMClient(provider="openrouter", openrouter_api_key="", api_key="")
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            client.openrouter_api_key = ""
            client.api_key = ""
            with self.assertRaises(LLMConnectionError):
                client.generate(system_prompt="Test", user_prompt="Hello")

    def test_openrouter_dispatch_success(self):
        client = LLMClient(provider="openrouter", openrouter_api_key="mock_key")
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"choices": [{"message": {"content": "Response from Kimi"}}]}'
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = client.generate(system_prompt="Test", user_prompt="Hello")
            self.assertEqual(res, "Response from Kimi")

    def test_auto_cascade_openrouter_to_local_llama_server(self):
        client = LLMClient(provider="auto", openrouter_api_key="mock_key")
        with patch.object(client, "_call_openrouter", side_effect=LLMConnectionError("Network disconnected")):
            with patch.object(client, "_call_llama_server", return_value="Local Phi-4 fallback online"):
                res = client.generate(system_prompt="Test", user_prompt="Hello")
                self.assertEqual(res, "Local Phi-4 fallback online")

    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused"))
    def test_ollama_unreachable_raises_connection_error(self, mock_urlopen):
        client = LLMClient(provider="ollama", api_base="http://127.0.0.1:59999")
        with self.assertRaises(LLMConnectionError):
            client.generate(system_prompt="Test", user_prompt="Hello")

    def test_openai_missing_key_raises_generation_error(self):
        client = LLMClient(provider="openai", api_key="")
        with self.assertRaises(LLMGenerationError):
            client.generate(system_prompt="Test", user_prompt="Hello")

    def test_explicit_fallback_offline_synthesis(self):
        client = LLMClient(provider="fallback")
        chunks = [{
            "chunk_id": "c1",
            "section_title": "Summary",
            "page_number": 1,
            "content": "AnyRAG provides hybrid dense and sparse BM25 retrieval.",
            "score": 0.95
        }]
        res = client.generate(system_prompt="Test", user_prompt="What does AnyRAG provide?", context_chunks=chunks)
        self.assertIn("AnyRAG provides hybrid dense and sparse BM25 retrieval", res)
        self.assertNotIn("[Ollama Error", res)
        self.assertNotIn("[API Error", res)
        self.assertNotIn("[llama.cpp Error", res)

    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused"))
    def test_all_providers_failed_raises_generation_error(self, mock_urlopen):
        client = LLMClient(provider="auto", api_base="http://127.0.0.1:59999", api_key=None, openrouter_api_key=None)
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            client.openrouter_api_key = ""
            with patch.object(client, "_call_llama_server", side_effect=LLMConnectionError("server offline")):
                with self.assertRaises(LLMGenerationError):
                    client.generate(system_prompt="Test", user_prompt="Hello", context_chunks=None)


class TestBM25Persistence(unittest.TestCase):
    """Test BM25Index save/load and VectorStore cache persistence."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_dir = Path(self.temp_dir) / "chromadb"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bm25_save_load_roundtrip(self):
        idx = BM25Index()
        idx.add_chunk("chunk_1", "hybrid dense and bm25 search", "doc_1")
        idx.add_chunk("chunk_2", "reciprocal rank fusion algorithm", "doc_1")
        idx.add_chunk("chunk_3", "completely unrelated text about biology", "doc_2")

        cache_path = Path(self.temp_dir) / "test_bm25.pkl"
        idx.save(cache_path)
        self.assertTrue(cache_path.exists())

        loaded_idx = BM25Index()
        self.assertTrue(loaded_idx.load(cache_path))
        self.assertEqual(loaded_idx.total_docs, 3)

        results = loaded_idx.search("hybrid bm25")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0][0], "chunk_1")

    def test_vectorstore_persists_bm25_cache(self):
        vs = VectorStore(self.db_dir)
        bm25_file = vs.bm25_path

        doc = ExtractedDocument(
            doc_id="doc_test_123",
            file_path=str(Path("sample.txt")),
            file_name="sample.txt",
            file_type="txt",
            file_size=500,
            sections=[ExtractedSection(content="Sparse BM25 test content", section_title="Main", page_number=1)],
            raw_text="Sparse BM25 test content"
        )
        chunk = DocumentChunk(
            chunk_id="chk_1",
            doc_id="doc_test_123",
            doc_name="sample.txt",
            doc_path="sample.txt",
            chunk_index=0,
            content="Sparse BM25 test content",
            section_title="Main",
            page_number=1
        )
        embedding = np.random.randn(1, 384).astype(np.float32)

        vs.add_document_and_chunks(doc, [chunk], embedding)
        self.assertTrue(bm25_file.exists())

        # Second VectorStore instance on the same directory
        vs2 = VectorStore(self.db_dir)
        self.assertEqual(vs2.bm25.total_docs, 1)

        # Verify BM25 search works from loaded cache
        hits = vs2.bm25.search("Sparse BM25")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0], "chk_1")

        # Purge document and verify cache stays updated
        vs2.purge_document("doc_test_123")
        self.assertEqual(vs2.bm25.total_docs, 0)

        vs3 = VectorStore(self.db_dir)
        self.assertEqual(vs3.bm25.total_docs, 0)


class TestWarmLlamaServerManager(unittest.TestCase):
    """Test warm LlamaServerManager setup and interfaces."""

    def test_manager_configuration(self):
        mgr = LlamaServerManager(port=8087, ctx_size=2048)
        self.assertEqual(mgr.port, 8087)
        self.assertEqual(mgr.ctx_size, 2048)
        self.assertEqual(mgr.server_url, "http://127.0.0.1:8087")
        self.assertFalse(mgr.is_healthy())


class TestLibraryImportsAndLogging(unittest.TestCase):
    """Test public library import and logging behavior."""

    def test_public_imports(self):
        import backend as anyrag
        self.assertEqual(anyrag.__version__, "0.1.0")
        self.assertTrue(hasattr(anyrag, "AnyRAG"))
        self.assertTrue(hasattr(anyrag, "VectorStore"))
        self.assertTrue(hasattr(anyrag, "BM25Index"))
        self.assertTrue(hasattr(anyrag, "LLMClient"))
        self.assertTrue(hasattr(anyrag, "LLMError"))
        self.assertTrue(hasattr(anyrag, "LLMConnectionError"))
        self.assertTrue(hasattr(anyrag, "LLMGenerationError"))
        self.assertTrue(hasattr(anyrag, "LlamaServerManager"))
        self.assertTrue(hasattr(anyrag, "parse_document"))

    def test_logging_silencing(self):
        logger = logging.getLogger("anyrag")
        orig_level = logger.level
        logger.setLevel(logging.CRITICAL)
        self.assertEqual(logger.level, logging.CRITICAL)
        logger.setLevel(orig_level)


class TestSmartPDFComplexityDetection(unittest.TestCase):
    """Test fast heuristic pre-scan detecting complex vs standard PDFs."""

    def test_simple_pdf_not_complex(self):
        import fitz
        from backend.parsers.pdf_parser import detect_pdf_complexity
        doc = fitz.open()
        p = doc.new_page()
        p.insert_text((50, 50), "This is a simple corporate quarterly report with standard text.")
        is_complex, reason = detect_pdf_complexity(doc)
        self.assertFalse(is_complex)
        self.assertIn("Standard narrative", reason)

    def test_math_formula_pdf_detected_complex(self):
        import fitz
        from backend.parsers.pdf_parser import detect_pdf_complexity
        doc = fitz.open()
        p = doc.new_page()
        # Insert dense math symbols: ∫, ∑, ∂, √, ≤, ≥, ≠, ∞, etc.
        p.insert_text((50, 50), "Theorem 1: \u222b f(x)dx = \u2211 \u221a(x^2 + y^2) \u2264 \u221e \u2202z/\u2202x \u2260 0 \u03c0 \u03b8 \u03bb \u2208 \u211d")
        is_complex, reason = detect_pdf_complexity(doc)
        self.assertTrue(is_complex)
        self.assertIn("Dense mathematical", reason)


if __name__ == "__main__":
    unittest.main()

