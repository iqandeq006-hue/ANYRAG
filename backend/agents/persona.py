import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from backend.storage.vector_store import VectorStore
from backend.embeddings.embedder import get_embedder
from .llm_client import LLMClient

logger = logging.getLogger("anyrag.persona")


class DocumentPersona:
    """
    Autonomous grounded conversational agent for a specific document.

    Features:
    - Soul file loading: reads a .md file to define the persona's worldview,
      stance, grounding rules, and personality instead of hardcoded prompts.
    - Persistent conversation log (convo.jsonl): lossless append-only record
      of every turn with timestamps, speaker, query, answer, and citations.
    - Rolling summary (summary.md): compressed working memory updated every
      N turns, used to keep long debates focused without token bloat.
    - Anchor question injection: the original debate question is re-injected
      into every prompt to prevent topic drift.
    """

    def __init__(
        self,
        doc_id: str,
        vector_store: VectorStore,
        persona_name: Optional[str] = None,
        soul_file: Optional[Union[str, Path]] = None,
        session_dir: Optional[Union[str, Path]] = None,
        llm_client: Optional[LLMClient] = None,
        anchor_question: Optional[str] = None,
        summary_interval: int = 4,
    ):
        self.doc_id = doc_id
        self.vector_store = vector_store
        self.doc_info = self.vector_store.get_document(doc_id)
        if not self.doc_info:
            raise ValueError(f"Document ID '{doc_id}' not found in vector store.")

        self.doc_name = self.doc_info["file_name"]
        self.persona_name = persona_name or f"Jarvis-{self.doc_name.split('.')[0][:10]}"
        self.llm = llm_client or LLMClient()
        self.embedder = get_embedder()
        self.anchor_question = anchor_question
        self.summary_interval = summary_interval

        # Soul file: defines the persona's worldview and grounding rules
        self.soul_text: Optional[str] = None
        if soul_file:
            soul_path = Path(soul_file)
            if soul_path.exists():
                self.soul_text = soul_path.read_text(encoding="utf-8").strip()
                logger.info(f"Loaded soul file for {self.persona_name}: {soul_path.name}")
            else:
                logger.warning(f"Soul file not found: {soul_path}. Using default system prompt.")

        # Persistent session storage
        self.session_dir: Optional[Path] = None
        self.convo_path: Optional[Path] = None
        self.summary_path: Optional[Path] = None
        if session_dir:
            self.session_dir = Path(session_dir)
            self.session_dir.mkdir(parents=True, exist_ok=True)
            self.convo_path = self.session_dir / "convo.jsonl"
            self.summary_path = self.session_dir / f"summary_{self.persona_name}.md"

        # In-memory state
        self.history: List[Dict[str, Any]] = []
        self.turn_count: int = 0
        self.rolling_summary: str = ""

        # Load existing session state if resuming
        self._load_session()

    # ──────────────────── Soul & System Prompt ────────────────────

    def get_system_prompt(self) -> str:
        """
        Build the system prompt from:
        1. Soul file (if loaded) — defines personality, stance, grounding rules.
        2. Anchor question (if set) — prevents topic drift in multi-turn debates.
        3. Rolling summary (if exists) — compressed memory of prior conversation.
        Falls back to default Jarvis prompt if no soul file is loaded.
        """
        if self.soul_text:
            prompt = self.soul_text
            # Inject document context reference
            prompt += f"\n\n[Document Binding: You are grounded to '{self.doc_name}'. Only cite facts from this document.]"
        else:
            prompt = (
                f"You are '{self.persona_name}', a specialized AI assistant and expert on the document '{self.doc_name}'.\n"
                f"Your role is to explain, summarize, and answer questions about this document accurately and concisely.\n"
                f"Rules:\n"
                f"1. Ground your answers strictly in the provided document context.\n"
                f"2. If the context does not contain the answer, state that the document does not mention it.\n"
                f"3. Be direct, articulate, and helpful (Jarvis style) without unnecessary filler."
            )

        if self.anchor_question:
            prompt += f"\n\n[Anchor Topic]: The core question being investigated is: \"{self.anchor_question}\". Always tie your responses back to this topic."

        if self.rolling_summary:
            prompt += f"\n\n[Prior Conversation Summary]:\n{self.rolling_summary}"

        # Inject immediate unsummarized recent turns (last 2-3 turns) so the persona never loses track of its stance
        recent_unsummarized = self.history[-2:] if self.history else []
        if recent_unsummarized:
            turns_snippet = "\n".join(
                f"- Turn {t['turn']} [{t.get('persona', 'Speaker')}]: {t.get('answer', '')}"
                for t in recent_unsummarized
            )
            prompt += f"\n\n[Immediate Recent Stance / Prior Turns]:\n{turns_snippet}"

        return prompt

    # ──────────────────── Core Ask ────────────────────

    def ask(
        self,
        query: str,
        retrieval_query: Optional[str] = None,
        top_k: int = 4,
        speaker: str = "user"
    ) -> Dict[str, Any]:
        """
        Ask a question to this document persona.
        Retrieves grounded context using clean retrieval_query (without prompt scaffolding),
        generates answer, persists to convo.jsonl, and triggers rolling summary update.
        """
        self.turn_count += 1
        search_text = retrieval_query or query
        query_vec = self.embedder.embed_query(search_text)
        chunks = self.vector_store.hybrid_search(
            query_text=search_text,
            query_vector=query_vec,
            top_k=top_k,
            doc_ids=[self.doc_id]
        )

        answer = self.llm.generate(
            system_prompt=self.get_system_prompt(),
            user_prompt=query,
            context_chunks=chunks
        )


        # Build turn record
        turn_record = {
            "turn": self.turn_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "speaker": speaker,
            "persona": self.persona_name,
            "query": query,
            "answer": answer,
            "citations": [
                {
                    "section": c.get("section_title", ""),
                    "score": round(c.get("score", 0), 3),
                    "page": c.get("page_number"),
                    "content_preview": c["content"][:150]
                }
                for c in chunks
            ]
        }

        self.history.append(turn_record)
        self._append_convo(turn_record)

        # Trigger rolling summary update at configured interval
        if self.turn_count % self.summary_interval == 0:
            self._update_rolling_summary()

        return {
            "persona_name": self.persona_name,
            "document": self.doc_name,
            "turn": self.turn_count,
            "query": query,
            "answer": answer,
            "retrieved_chunks": chunks
        }

    # ──────────────────── Persistent Conversation Log ────────────────────

    def _append_convo(self, turn_record: Dict[str, Any]):
        """Append a single turn to the persistent convo.jsonl file."""
        if not self.convo_path:
            return
        try:
            with open(self.convo_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(turn_record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write conversation log: {e}")

    def _load_session(self):
        """Load existing conversation history and rolling summary from disk."""
        # Load conversation log
        if self.convo_path and self.convo_path.exists():
            try:
                with open(self.convo_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            record = json.loads(line)
                            self.history.append(record)
                self.turn_count = len(self.history)
                logger.info(f"Resumed session for {self.persona_name}: {self.turn_count} turns loaded from {self.convo_path.name}")
            except Exception as e:
                logger.warning(f"Failed to load conversation log: {e}")

        # Load rolling summary
        if self.summary_path and self.summary_path.exists():
            try:
                self.rolling_summary = self.summary_path.read_text(encoding="utf-8").strip()
                if self.rolling_summary:
                    logger.info(f"Loaded rolling summary for {self.persona_name} ({len(self.rolling_summary)} chars)")
            except Exception as e:
                logger.warning(f"Failed to load rolling summary: {e}")

    # ──────────────────── Rolling Summary ────────────────────

    def _update_rolling_summary(self):
        """
        Generate a compressed rolling summary of the conversation so far.
        This replaces passing the entire raw dialogue history into each prompt.
        """
        if not self.history:
            return

        # Build the last N turns for summarization
        recent_turns = self.history[-self.summary_interval:]
        turns_text = "\n".join(
            f"Turn {t['turn']} [{t.get('speaker', 'user')}]: {t['query']}\n"
            f"{t['persona']}: {t['answer']}"
            for t in recent_turns
        )

        summary_prompt = (
            f"You are summarizing the conversation history for the persona '{self.persona_name}'.\n"
            f"Write a concise summary (max 150 words) capturing:\n"
            f"1. Key facts discussed and cited from the document.\n"
            f"2. Agreements or conclusions reached.\n"
            f"3. Open questions or unresolved points.\n"
            f"Write in {self.persona_name}'s voice. Do not fabricate facts."
        )

        existing_context = f"Previous summary:\n{self.rolling_summary}\n\n" if self.rolling_summary else ""

        try:
            new_summary = self.llm.generate(
                system_prompt=summary_prompt,
                user_prompt=f"{existing_context}New conversation turns to incorporate:\n{turns_text}",
                context_chunks=None
            )
            self.rolling_summary = new_summary.strip()

            # Persist to disk
            if self.summary_path:
                self.summary_path.write_text(
                    f"# Rolling Summary — {self.persona_name}\n"
                    f"_Updated: {datetime.now(timezone.utc).isoformat()}_\n\n"
                    f"{self.rolling_summary}\n",
                    encoding="utf-8"
                )
                logger.info(f"Rolling summary updated for {self.persona_name} (turn {self.turn_count})")
        except Exception as e:
            logger.warning(f"Failed to update rolling summary: {e}")

    # ──────────────────── Utilities ────────────────────

    def get_conversation_log(self) -> List[Dict[str, Any]]:
        """Return the full in-memory conversation history."""
        return self.history

    def get_summary(self) -> str:
        """Return the current rolling summary."""
        return self.rolling_summary

    def set_anchor_question(self, question: str):
        """Set or update the anchor question for topic drift prevention."""
        self.anchor_question = question
        logger.info(f"Anchor question set for {self.persona_name}: '{question[:80]}...'")
