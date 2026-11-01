# AnyRAG — Goal & Philosophy

## The One-Sentence Mission
A modular library that turns any document into an autonomous, human-sounding conversational persona ("Doc Jarvis") and lets two personas debate each other with you at the roundtable — grounded strictly in facts, conversational by design, and private to your machine.

---

## Why This Exists (The Core Vision)
Every generic "chat with your docs" tool dumps robotic, paragraph-heavy summaries or returns search snippets. AnyRAG is built on a fundamentally different premise:

1. **People, not search engines**: You are not running a search query. You are instantiating specialized people who have deeply studied specific documents and can explain them, defend them, and argue their merits with human cadence.
2. **Tri-party conversational debate**: Real understanding doesn't come from reading a diff report — it comes from hearing two opposing viewpoints debate an issue in real time while you interject, challenge, and steer the conversation.
3. **Speakable, human responses**: Real people don't speak in bulleted markdown essays. Debate turns must be 2 to 4 punchy, natural sentences (under 90 words), full of authentic verbal transitions ("Look,", "Here's the thing —", "I'll give you that, but..."), and ready for voice/HUD interaction.
4. **Library first, not an isolated app**: AnyRAG is a reusable core engine designed to seamlessly plug into desktop overlays, custom PyQt HUDs, or ecosystem agents without imposing web bloat.

---

## The Core Principles

### 1. Speakable Human Dialogue ("Roundtable, Not an Essay")
Personas sound like sharp humans at a whiteboard or courtroom table, not textbook generators.
- **Short & punchy**: 2–4 sentences per turn, spoken cadence, natural rhythm variation.
- **Human discourse mechanics**: Personas think out loud, concede valid points gracefully ("I'll give you that"), challenge weak logic without hostility, and use direct analogies.
- **No robotic formatting**: Zero markdown bullet dumps or academic disclaimers in dialogue turns.

### 2. Tri-Party Debate Architecture
Debates take two distinct forms based on document scope:
- **Same Document Debate (Single Index, Shared DB)**:
  When two personas debate different interpretations or angles of the *same* document, they share one ChromaDB & BM25 index. There is zero reason to duplicate embeddings. Their divergence is driven entirely by their **Soul Markdown** (`docs/souls/default.md`) and session history.
- **Cross-Document Debate (Dual Indexes, Isolated DBs)**:
  When comparing two distinct files (e.g., Paper A vs. Paper B), each persona gets an isolated `VectorStore` instance. This creates an unbreakable physical knowledge barrier preventing fact cross-contamination.
- **The Human in the Loop**:
  You are the third party at the table. You can listen as the personas debate autonomously, or step in at any turn to cross-examine either side.

### 3. Debate Intelligence Tools (`diff` & `compare`)
Vector operations serve the debate, not just standalone CLI reports:
- **Pre-Debate Semantic Diff (`anyrag diff`)**:
  Before cross-document debate rounds begin, a chunk-level cosine matrix (`np.matmul`) maps out:
  - *Overlap Zone (≥ 0.70)*: Consensus facts — debate skips these.
  - *Unique Zones (≤ 0.40)*: Claims exclusive to one document.
  - *Contradiction Zone (0.40–0.70)*: Hotspot where both documents discuss the same concept with diverging conclusions — this is where the debate focuses.
- **Targeted Cross-Retrieval (`anyrag compare`)**:
  Live multi-document RAG retrieval to pull simultaneous counter-evidence when one persona challenges another's specific claim.

### 4. Lossless Transcript + Compressed Working Memory
Multi-turn debates die when token bloat occurs or topics drift:
- **`convo.jsonl` (Lossless Log)**: Append-only persistent record storing full turns, exact timestamps, speaker labels, query/responses, and chunk citations for audit, replay, or overlay UI rendering.
- **`summary_{persona}.md` (Rolling Memory)**: Every few turns, recent dialogue is synthesized into a concise 150-word memory written in that persona's voice, preventing context window exhaustion.
- **Anchor Question Re-Injection**: The core inquiry is continuously bound into the system prompt to stop personas from getting lost in semantic weeds.

### 5. High-Speed Cloud Primary with Warm Offline Fallback
- **Primary Cloud**: High-reasoning cloud LLMs (OpenRouter Kimi-k2 / DeepSeek-R1 / DeepSeek-Chat) for rapid, nuanced, articulate debate turns.
- **Offline Backup**: Standalone warm `llama-server` process hosting local GGUF weights (`phi-4-mini`) ensuring uninterrupted debate capability even when offline or disconnected.
- **Local Sovereignty**: Document indexing, vector embeddings (`all-MiniLM-L6-v2`), and ChromaDB storage always execute 100% locally on your machine.
- **Strict Guardrails**: Read-only ingestion sandboxed exclusively to user directories (`Documents`, `Downloads`, `Pictures`, `Videos`).

---

## What AnyRAG Is Not
- **Not a generic search assistant**: It does not scrape random web pages or hallucinate general knowledge. If the document doesn't say it, the persona states it doesn't know.
- **Not bloatware**: Zero heavy Node/Electron runtimes or extraneous background daemons.
- **Not a monologuing lecturer**: Any persona delivering an essay has failed the fundamental design criteria.
