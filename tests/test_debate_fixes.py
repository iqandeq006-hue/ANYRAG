import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

import numpy as np

from backend.agents.comparator import DocumentComparator
from backend.agents.persona import DocumentPersona
from backend.agents.debate import DebateSession
from backend.storage.vector_store import VectorStore
from backend.parsers.base import ExtractedDocument, ExtractedSection
from backend.chunking.chunker import DocumentChunk


class TestDebateEngineFixes(unittest.TestCase):
    """Tests for the 3 critical debate engine bugfixes:
    1. Cross-doc dual vector store support in DocumentComparator.
    2. Decoupled clean retrieval query without prompt scaffolding.
    3. Hybrid memory: unsummarized recent turns preserved in system prompt.
    """

    def setUp(self):
        self.temp_dir_1 = tempfile.mkdtemp()
        self.temp_dir_2 = tempfile.mkdtemp()
        self.vs1 = VectorStore(db_path=self.temp_dir_1)
        self.vs2 = VectorStore(db_path=self.temp_dir_2)

        # Mock LLM Client
        self.mock_llm = MagicMock()
        self.mock_llm.generate.return_value = "Mocked articulate debate statement."

        # Add Doc A to VS1
        doc_a = ExtractedDocument(
            doc_id="doc_a_123", file_path="doc_a.txt", file_name="doc_a.txt", file_type="txt", file_size=100,
            sections=[ExtractedSection(section_title="Methodology", content="Paper A uses Method Alpha with high precision.")]
        )
        chunk_a = DocumentChunk(
            chunk_id="doc_a_123_c0", doc_id="doc_a_123", doc_name="doc_a.txt", doc_path="doc_a.txt",
            content="Paper A uses Method Alpha with high precision.",
            chunk_index=0, section_title="Methodology"
        )
        vec_a = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        self.vs1.add_document_and_chunks(doc_a, [chunk_a], vec_a)
        self.doc_a_id = "doc_a_123"

        # Add Doc B to VS2 (Isolated Store!)
        doc_b = ExtractedDocument(
            doc_id="doc_b_456", file_path="doc_b.txt", file_name="doc_b.txt", file_type="txt", file_size=100,
            sections=[ExtractedSection(section_title="Results", content="Paper B uses Method Beta with faster inference.")]
        )
        chunk_b = DocumentChunk(
            chunk_id="doc_b_456_c0", doc_id="doc_b_456", doc_name="doc_b.txt", doc_path="doc_b.txt",
            content="Paper B uses Method Beta with faster inference.",
            chunk_index=0, section_title="Results"
        )
        vec_b = np.array([[0.0, 1.0, 0.0]], dtype=np.float32)
        self.vs2.add_document_and_chunks(doc_b, [chunk_b], vec_b)
        self.doc_b_id = "doc_b_456"



    def tearDown(self):
        shutil.rmtree(self.temp_dir_1, ignore_errors=True)
        shutil.rmtree(self.temp_dir_2, ignore_errors=True)

    def test_cross_doc_comparator_reads_both_isolated_stores(self):
        """Bug 1: Verify comparator correctly queries vs1 and vs2 without missing chunks."""
        comparator = DocumentComparator(
            doc1_id=self.doc_a_id,
            doc2_id=self.doc_b_id,
            vector_store=self.vs1,
            vector_store_2=self.vs2,
            llm_client=self.mock_llm
        )
        diff_res = comparator.compute_semantic_diff()
        self.assertNotIn("error", diff_res)
        self.assertEqual(diff_res["doc1_name"], "doc_a.txt")
        self.assertEqual(diff_res["doc2_name"], "doc_b.txt")
        # Dot product of [1,0,0] and [0,1,0] is 0 -> orthogonal / unique
        self.assertEqual(diff_res["overall_semantic_similarity"], 0.0)
        self.assertEqual(diff_res["unique_doc1_count"], 1)
        self.assertEqual(diff_res["unique_doc2_count"], 1)

    def test_retrieval_query_decoupling(self):
        """Bug 2: Verify persona.ask() searches with retrieval_query when provided."""
        persona = DocumentPersona(
            doc_id=self.doc_a_id,
            vector_store=self.vs1,
            llm_client=self.mock_llm
        )
        with unittest.mock.patch.object(persona.vector_store, "hybrid_search", wraps=persona.vector_store.hybrid_search) as mock_search:
            persona.ask(
                query="[DEBATE SCAFFOLDING PROMPT WITH 100 INSTRUCTIONS]",
                retrieval_query="Method Alpha",
                top_k=2
            )
            # Verify the search was invoked with clean 'Method Alpha', NOT scaffolding!
            self.assertTrue(mock_search.called)
            called_kwargs = mock_search.call_args[1]
            self.assertEqual(called_kwargs["query_text"], "Method Alpha")

    def test_hybrid_memory_retains_recent_turns(self):
        """Bug 3: Verify persona system prompt includes recent unsummarized turns."""
        persona = DocumentPersona(
            doc_id=self.doc_a_id,
            vector_store=self.vs1,
            llm_client=self.mock_llm,
            summary_interval=5
        )
        self.mock_llm.generate.return_value = "I argue that Method Alpha is superior due to error bounds."
        persona.ask(query="What is your stance?")

        prompt = persona.get_system_prompt()
        self.assertIn("[Immediate Recent Stance / Prior Turns]:", prompt)
        self.assertIn("Method Alpha is superior", prompt)

    def test_autonomous_objection_pass_when_accurate(self):
        """Verify listener outputs None when statement is uncontested [PASS]."""
        session = DebateSession(
            doc1_id=self.doc_a_id, vector_store_1=self.vs1,
            doc2_id=self.doc_b_id, vector_store_2=self.vs2,
            llm_client=self.mock_llm
        )
        self.mock_llm.generate.return_value = "[PASS]"
        objection = session.evaluate_objection(
            listener_persona=session.persona_b,
            spoken_statement="Method Alpha is tested thoroughly.",
            speaker_name="Advocate-A"
        )
        self.assertIsNone(objection)

    def test_autonomous_objection_triggers_on_contradiction(self):
        """Verify listener raises objection when a document conflict exists."""
        session = DebateSession(
            doc1_id=self.doc_a_id, vector_store_1=self.vs1,
            doc2_id=self.doc_b_id, vector_store_2=self.vs2,
            llm_client=self.mock_llm
        )
        self.mock_llm.generate.return_value = "Hold on — Paper B proves inference is 3x faster with Beta."
        objection = session.evaluate_objection(
            listener_persona=session.persona_b,
            spoken_statement="Alpha has the fastest runtime known.",
            speaker_name="Advocate-A"
        )
        self.assertIsNotNone(objection)
        self.assertEqual(objection["objector"], session.persona_b.persona_name)
        self.assertIn("Paper B proves inference", objection["statement"])

    def test_check_user_statement_deduplication(self):
        """Verify that if both personas flag the user, only one speaks and avoids duplicate shouting."""
        session = DebateSession(
            doc1_id=self.doc_a_id, vector_store_1=self.vs1,
            doc2_id=self.doc_b_id, vector_store_2=self.vs2,
            llm_client=self.mock_llm
        )
        self.mock_llm.generate.return_value = "Correction: Neither paper claims 100% precision."
        deduped = session.check_user_statement("Both of your papers claim 100% precision!")
        self.assertIsNotNone(deduped)
        # Exactly one persona speaks the objection
        self.assertIn(deduped["objector"], [session.persona_a.persona_name, session.persona_b.persona_name])
        # The other persona is marked as concurred without repeating the speech
        self.assertIn("concurred and yielded", deduped.get("note", ""))


if __name__ == "__main__":
    unittest.main()


