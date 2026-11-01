import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from backend.storage.vector_store import VectorStore
from backend.embeddings.embedder import get_embedder
from .llm_client import LLMClient
from .persona import DocumentPersona
from .comparator import DocumentComparator

logger = logging.getLogger("anyrag.debate")



class DebateSession:
    """
    Tri-Party Debate Engine: Two document personas debate each other
    with the user as the third participant.

    Architecture:
    - Same-document debate: Both personas share a single VectorStore/engine.
      Differentiation comes from soul files and conversation histories.
    - Cross-document debate: Each persona gets its own VectorStore to
      prevent knowledge contamination. Pre-debate diff maps contradiction zones.

    Features:
    - Soul file per persona (loaded from .md files)
    - Speakable responses: max 60-90 words, conversational, no essays
    - Persistent dual-file storage:
      - convo.jsonl: lossless full dialogue transcript
      - summary_{persona}.md: rolling compressed memory per persona
    - Anchor question re-injection every turn to prevent topic drift
    - Pre-debate semantic diff (cross-doc only) to identify debate hotspots
    """

    def __init__(
        self,
        doc1_id: str,
        vector_store_1: VectorStore,
        doc2_id: Optional[str] = None,
        vector_store_2: Optional[VectorStore] = None,
        soul_file_a: Optional[Union[str, Path]] = None,
        soul_file_b: Optional[Union[str, Path]] = None,
        persona_name_a: Optional[str] = None,
        persona_name_b: Optional[str] = None,
        session_dir: Optional[Union[str, Path]] = None,
        llm_client: Optional[LLMClient] = None,
        summary_interval: int = 4,
    ):
        """
        Initialize a debate session.

        Same-document debate:
            DebateSession(doc1_id="doc_abc", vector_store_1=shared_vs)

        Cross-document debate:
            DebateSession(
                doc1_id="doc_a", vector_store_1=vs_a,
                doc2_id="doc_b", vector_store_2=vs_b
            )
        """
        self.llm = llm_client or LLMClient()
        self.is_cross_doc = doc2_id is not None and doc2_id != doc1_id

        # Session directory for persistent storage
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_dir = Path("data") / "debates" / f"debate_{ts}"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.convo_path = self.session_dir / "convo.jsonl"
        self.anchor_question: Optional[str] = None
        self.turn_count: int = 0
        self.debate_log: List[Dict[str, Any]] = []

        # Pre-debate diff results (cross-doc only)
        self.pre_diff: Optional[Dict[str, Any]] = None

        # Build Persona A
        vs_a = vector_store_1
        self.persona_a = DocumentPersona(
            doc_id=doc1_id,
            vector_store=vs_a,
            persona_name=persona_name_a or "Advocate-A",
            soul_file=soul_file_a,
            session_dir=self.session_dir / "persona_a",
            llm_client=self.llm,
            summary_interval=summary_interval,
        )

        # Build Persona B
        actual_doc2 = doc2_id or doc1_id
        vs_b = vector_store_2 if vector_store_2 else vector_store_1
        self.persona_b = DocumentPersona(
            doc_id=actual_doc2,
            vector_store=vs_b,
            persona_name=persona_name_b or "Advocate-B",
            soul_file=soul_file_b,
            session_dir=self.session_dir / "persona_b",
            llm_client=self.llm,
            summary_interval=summary_interval,
        )

        # Load existing debate log if resuming
        self._load_debate_log()

        logger.info(
            f"DebateSession initialized: {self.persona_a.persona_name} vs {self.persona_b.persona_name} "
            f"({'cross-doc' if self.is_cross_doc else 'same-doc'}) "
            f"| Session: {self.session_dir}"
        )

    # ──────────────────── Pre-Debate Intelligence ────────────────────

    def run_pre_debate_diff(self) -> Optional[Dict[str, Any]]:
        """
        Run vectorized semantic diff between documents before the debate starts.
        Only meaningful for cross-document debates.
        Passes both persona vector stores to ensure isolated, uncontaminated retrieval.
        Returns the overlap/unique/contradiction zone map.
        """
        if not self.is_cross_doc:
            logger.info("Same-document debate — skipping pre-debate diff (nothing to diff).")
            return None

        comparator = DocumentComparator(
            doc1_id=self.persona_a.doc_id,
            doc2_id=self.persona_b.doc_id,
            vector_store=self.persona_a.vector_store,
            vector_store_2=self.persona_b.vector_store,
            llm_client=self.llm
        )
        self.pre_diff = comparator.compute_semantic_diff()
        logger.info(
            f"Pre-debate diff complete: {self.pre_diff['common_topics_count']} overlaps, "
            f"{self.pre_diff['unique_doc1_count']} unique to A, "
            f"{self.pre_diff['unique_doc2_count']} unique to B"
        )
        return self.pre_diff

    # ──────────────────── Debate Turn Execution ────────────────────

    def start_debate(self, question: str) -> Dict[str, Any]:
        """
        Launch the debate with an anchor question.
        Both personas give their opening statements.
        Returns the opening round result.
        """
        self.anchor_question = question
        self.persona_a.set_anchor_question(question)
        self.persona_b.set_anchor_question(question)

        # Run pre-debate diff for cross-doc debates
        if self.is_cross_doc and not self.pre_diff:
            self.run_pre_debate_diff()

        # Opening statement from Persona A (clean retrieval on anchor question)
        opening_prompt_a = self._build_debate_prompt(
            question, speaker="user", target="a", is_opening=True
        )
        result_a = self.persona_a.ask(
            query=opening_prompt_a,
            retrieval_query=question,
            top_k=4,
            speaker="user"
        )

        # Opening statement from Persona B (sees A's opening, searches anchor + A's claim)
        opening_prompt_b = self._build_debate_prompt(
            question, speaker="user", target="b", is_opening=True,
            opponent_last_statement=result_a["answer"]
        )
        retrieval_b = f"{question} {result_a['answer']}"[:200]
        result_b = self.persona_b.ask(
            query=opening_prompt_b,
            retrieval_query=retrieval_b,
            top_k=4,
            speaker="user"
        )

        # Record opening round
        opening_round = {
            "round": 1,
            "anchor_question": question,
            "persona_a": {
                "name": self.persona_a.persona_name,
                "statement": result_a["answer"]
            },
            "persona_b": {
                "name": self.persona_b.persona_name,
                "statement": result_b["answer"]
            }
        }

        self.turn_count = 1
        self.debate_log.append(opening_round)
        self._append_debate_turn(opening_round)

        return opening_round

    def next_round(self, user_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the next debate round.
        Optional user_input allows the user to steer the debate or challenge.
        If no user_input, personas continue debating each other.
        Clean substantive claims are passed to retrieval_query without prompt scaffolding.
        """
        self.turn_count += 1

        # Get last statements for context
        last_round = self.debate_log[-1] if self.debate_log else None
        last_b_statement = last_round["persona_b"]["statement"] if last_round else ""
        last_a_statement = last_round["persona_a"]["statement"] if last_round else ""

        # Build prompt for Persona A
        if user_input:
            prompt_a = self._build_debate_prompt(
                user_input, speaker="user", target="a",
                opponent_last_statement=last_b_statement
            )
            clean_search_a = f"{self.anchor_question or ''} {user_input} {last_b_statement}"[:200]
        else:
            prompt_a = self._build_debate_prompt(
                f"Respond to {self.persona_b.persona_name}'s last argument.",
                speaker="debate", target="a",
                opponent_last_statement=last_b_statement
            )
            clean_search_a = f"{self.anchor_question or ''} {last_b_statement}"[:200]

        result_a = self.persona_a.ask(
            query=prompt_a,
            retrieval_query=clean_search_a,
            top_k=3,
            speaker=user_input and "user" or "debate"
        )

        # Build prompt for Persona B (reacts to A's new statement)
        if user_input:
            prompt_b = self._build_debate_prompt(
                user_input, speaker="user", target="b",
                opponent_last_statement=result_a["answer"]
            )
            clean_search_b = f"{self.anchor_question or ''} {user_input} {result_a['answer']}"[:200]
        else:
            prompt_b = self._build_debate_prompt(
                f"Respond to {self.persona_a.persona_name}'s last argument.",
                speaker="debate", target="b",
                opponent_last_statement=result_a["answer"]
            )
            clean_search_b = f"{self.anchor_question or ''} {result_a['answer']}"[:200]

        result_b = self.persona_b.ask(
            query=prompt_b,
            retrieval_query=clean_search_b,
            top_k=3,
            speaker=user_input and "user" or "debate"
        )


        round_record = {
            "round": self.turn_count,
            "user_input": user_input,
            "anchor_question": self.anchor_question,
            "persona_a": {
                "name": self.persona_a.persona_name,
                "statement": result_a["answer"]
            },
            "persona_b": {
                "name": self.persona_b.persona_name,
                "statement": result_b["answer"]
            }
        }

        self.debate_log.append(round_record)
        self._append_debate_turn(round_record)

        return round_record

    # ──────────────────── Autonomous Objection & Background Listener ────────────────────

    def evaluate_objection(
        self,
        listener_persona: DocumentPersona,
        spoken_statement: str,
        speaker_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Autonomous watchdog logic:
        A persona listens to what was just spoken (by user or other persona).
        It inspects its grounded document:
        - If there is a factual conflict, mistake, or distortion: It generates a sharp 2-3 sentence objection.
        - If the statement is factually accurate or there is no document contradiction: It returns None (silent PASS).
        """
        # Clean search query targeting the statement's substantive claims
        clean_search = f"{self.anchor_question or ''} {spoken_statement}"[:200]
        chunks = listener_persona.vector_store.hybrid_search(
            query_text=clean_search,
            query_vector=listener_persona.embedder.embed_query(clean_search),
            top_k=3,
            doc_ids=[listener_persona.doc_id]
        )

        objection_system_prompt = (
            f"You are '{listener_persona.persona_name}', grounded strictly to '{listener_persona.doc_name}'.\n"
            f"You are actively listening at a roundtable. {speaker_name} just made a statement.\n\n"
            "INSTRUCTIONS:\n"
            "1. Check if the statement factually contradicts, distorts, or misrepresents evidence in YOUR document.\n"
            "2. If there IS a clear factual error or contradiction: Speak up immediately to object and correct it. "
            "Keep it sharp, speakable: 2 to 3 sentences max (under 75 words). Cite your document's facts.\n"
            "3. If the statement is ACCURATE, UNCONTESTED, or your document has no contradictory evidence: "
            "Output EXACTLY and ONLY the word '[PASS]'. Do not say anything else."
        )

        objection_user_prompt = (
            f"Topic: {self.anchor_question or 'General'}\n"
            f"Speaker ({speaker_name}) stated:\n\"{spoken_statement}\"\n\n"
            "Do you object based on your document or [PASS]?"
        )

        response = self.llm.generate(
            system_prompt=objection_system_prompt,
            user_prompt=objection_user_prompt,
            context_chunks=chunks
        ).strip()

        # Check for silent pass
        if response.startswith("[PASS]") or response == "[PASS]":
            logger.info(f"{listener_persona.persona_name} verified statement and remained silent [PASS].")
            return None

        # Clean out any accidental formatting
        clean_objection = response.replace("[OBJECT]", "").strip()

        logger.info(f"{listener_persona.persona_name} autonomously raised an objection: {clean_objection[:80]}...")
        return {
            "objector": listener_persona.persona_name,
            "document": listener_persona.doc_name,
            "statement": clean_objection,
            "citations": [
                {
                    "section": c.get("section_title", ""),
                    "score": round(c.get("score", 0), 3),
                    "page": c.get("page_number"),
                    "preview": c["content"][:120]
                }
                for c in chunks
            ]
        }

    def _deduplicate_objections(
        self,
        objection_a: Optional[Dict[str, Any]],
        objection_b: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Deduplication rule:
        Only one persona speaks at a time.
        If both Persona A and Persona B flag a contradiction:
        - We compare their objections. If both caught the same issue, Persona A speaks first,
          and Persona B discards its flag since the point was already made.
        - If they raised different points, Persona A speaks the primary objection,
          and the other is logged without double-speaking at the user.
        """
        if not objection_a and not objection_b:
            return None
        if objection_a and not objection_b:
            return objection_a
        if objection_b and not objection_a:
            return objection_b

        # Both raised objections
        logger.info("Both personas flagged an objection. Applying single-speaker deduplication rule.")
        # Persona A delivers the objection; Persona B yields and discards redundant speech
        return {
            **objection_a,
            "co_signed_by": objection_b["objector"],
            "note": f"{objection_b['objector']} concurred and yielded to prevent redundant interruption."
        }

    def check_user_statement(self, user_statement: str) -> Optional[Dict[str, Any]]:
        """
        Both personas evaluate a user's statement against their respective documents.
        If the user is mistaken or contradicts grounded facts:
        - Exactly ONE persona speaks up to correct the user.
        - If both documents contradict the user, one speaks and the other discards its flag.
        """
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_a = executor.submit(self.evaluate_objection, self.persona_a, user_statement, "User")
            fut_b = executor.submit(self.evaluate_objection, self.persona_b, user_statement, "User")
            obj_a = fut_a.result()
            obj_b = fut_b.result()

        return self._deduplicate_objections(obj_a, obj_b)

    def address_persona(
        self,
        target: str,
        user_query: str,
        auto_interject: bool = True
    ) -> Dict[str, Any]:
        """
        Orchestrator method:
        The user addresses a specific persona ('a' or 'b') with a question or directive.
        - First, the system checks if the user's premise itself is factually flawed.
        - While the target persona answers, the listener persona pre-emptively queries in background.
        - If the listener spots a contradiction, it objects immediately after the speaker finishes.
        - Only one persona speaks at a time; redundant flags are discarded.
        """
        self.turn_count += 1
        speaker_persona = self.persona_a if target.lower() in ["a", "persona_a", "1"] else self.persona_b
        listener_persona = self.persona_b if speaker_persona == self.persona_a else self.persona_a

        # 1. Primary speaker answers user query
        speaker_result = speaker_persona.ask(
            query=user_query,
            retrieval_query=user_query,
            top_k=4,
            speaker="user"
        )
        speaker_text = speaker_result["answer"]

        objection_data = None
        # 2. In background / concurrent thread: listener checks for objection against the speaker's statement
        if auto_interject:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self.evaluate_objection,
                    listener_persona,
                    speaker_text,
                    speaker_persona.persona_name
                )
                objection_data = future.result()

        turn_payload = {
            "turn": self.turn_count,
            "addressed_target": target,
            "user_query": user_query,
            "primary_speaker": {
                "name": speaker_persona.persona_name,
                "statement": speaker_text,
                "document": speaker_persona.doc_name
            },
            "interjection": objection_data  # None if listener [PASS]ed, or Dict if objection raised
        }

        # Log into convo
        log_entry = {
            "round": self.turn_count,
            "type": "addressed_turn",
            "speaker": speaker_persona.persona_name,
            "statement": speaker_text,
            "interjection": objection_data
        }
        self.debate_log.append(log_entry)
        self._append_debate_turn(log_entry)

        return turn_payload



    # ──────────────────── Prompt Engineering ────────────────────

    def _build_debate_prompt(
        self,
        query: str,
        speaker: str,
        target: str,
        is_opening: bool = False,
        opponent_last_statement: Optional[str] = None
    ) -> str:
        """
        Build a debate-optimized prompt that enforces:
        1. Speakable length (2-4 sentences, max 90 words)
        2. Conversational tone (not an essay)
        3. Grounded in document facts
        4. Anchored to the original question
        """
        opponent_name = self.persona_b.persona_name if target == "a" else self.persona_a.persona_name

        parts = []

        # Anchor question reminder
        if self.anchor_question:
            parts.append(f"[DEBATE TOPIC]: \"{self.anchor_question}\"")

        if is_opening:
            parts.append(
                f"Give your opening position on this topic. Be direct and grounded in your document. "
                f"Keep it short: 2-4 sentences, under 90 words. Speak as if in a live debate."
            )
        else:
            parts.append(
                f"You are debating {opponent_name}. Respond to their argument. "
                f"Be sharp, conversational, and concise: 2-4 sentences, max 90 words. "
                f"Challenge weak points. Cite your document's evidence."
            )

        if opponent_last_statement:
            parts.append(f"\n[{opponent_name}'s last statement]: \"{opponent_last_statement}\"")

        if speaker == "user" and query:
            parts.append(f"\n[User's question/steering]: {query}")

        return "\n".join(parts)

    # ──────────────────── Persistence ────────────────────

    def _append_debate_turn(self, round_record: Dict[str, Any]):
        """Append a debate round to the persistent convo.jsonl."""
        try:
            enriched = {
                **round_record,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_type": "cross-doc" if self.is_cross_doc else "same-doc"
            }
            with open(self.convo_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(enriched, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write debate log: {e}")

    def _load_debate_log(self):
        """Load existing debate log from convo.jsonl for session resumption."""
        if self.convo_path.exists():
            try:
                with open(self.convo_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self.debate_log.append(json.loads(line))
                self.turn_count = len(self.debate_log)
                if self.debate_log:
                    self.anchor_question = self.debate_log[0].get("anchor_question")
                    self.persona_a.set_anchor_question(self.anchor_question or "")
                    self.persona_b.set_anchor_question(self.anchor_question or "")
                logger.info(f"Resumed debate session: {self.turn_count} rounds loaded")
            except Exception as e:
                logger.warning(f"Failed to load debate log: {e}")

    # ──────────────────── Utilities ────────────────────

    def get_debate_transcript(self) -> List[Dict[str, Any]]:
        """Return the full debate log."""
        return self.debate_log

    def get_status(self) -> Dict[str, Any]:
        """Return current debate session status."""
        return {
            "session_dir": str(self.session_dir),
            "mode": "cross-doc" if self.is_cross_doc else "same-doc",
            "persona_a": self.persona_a.persona_name,
            "persona_b": self.persona_b.persona_name,
            "doc_a": self.persona_a.doc_name,
            "doc_b": self.persona_b.doc_name,
            "anchor_question": self.anchor_question,
            "rounds_completed": self.turn_count,
            "has_pre_diff": self.pre_diff is not None,
        }
