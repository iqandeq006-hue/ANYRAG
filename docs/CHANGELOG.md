# AnyRAG — Complete Session History & Chronological Changelog

This single document accumulates both the **foundational session dialogue/requirements** and the **time-stamped chronological development changelog** tracking every modification and architectural advancement in AnyRAG.

---

# PART 1: Session Log & Requirements Specification

Verbatim accumulation of the conversation, requirements, and reference links. Preserved as originally specified.

---

## TURN 1 — Initial idea (dictated)

> Let's have a talk, and I want to tell me one thing. I want an any rag LLL. It's kind of like a LLM, not LLM. Okay. Agent. Any rag agent means whatever documents that I have, whatever. Okay? There is a specification right there itself. Documents, even PPT or docs, words, markdown files, any kind of things. Okay? I want to have a LLM over there, which will be containing the vector database having like embeddings, any documents, I want to put it inside this thing. Like, it's not putting it there. It's calling the LLM itself directly and asking it to have this document look through and telling it to explain what it contains and helping me to search anything. Like, context based over the document itself. I want this function right here. Like, whatever it might be. Okay? Whatever there is a specification there for itself also, like, any kind of document that is present, I want to have a rack because sometimes I don't want to skim through every single thing. want to have someone who can look up there and tell me what it contains and what it is there present. So it's kind of Jarvis level. Do you think what I'm trying to say you got it? Like, what's your opinion about that? Is there any some kind of research or kind of this exact product is actually available open source? Can I research on that and tell me about it? And and one thing, before researching, I wanted to do one thing. Recite what I just mentioned, what I am telling you. The use case or the idea. Validation is needed.

### Response

Here's my read on what you're describing, before I go digging:

**Your idea, restated:** A universal document-agnostic RAG agent. You point it at any files — PDFs, DOCX, PPTX, Markdown, whatever — it chunks and embeds them into a vector store automatically, and then you talk to an LLM that has retrieval access over that store. So instead of you skimming a file, you ask "what's in this?" or "find the part about X" and it pulls the relevant chunks and answers in context. Basically a personal "chat with your knowledge base" layer, format-agnostic, Jarvis-flavored.

That's a coherent, well-known pattern — not niche. It's usually called "chat with your docs," a "second brain" RAG app, or "personal knowledge assistant."

**Already-existing open source projects doing this:**
- **AnythingLLM** and **Open WebUI (+RAG)** — the most popular "point at a folder, get a chat-with-docs UI," support PDF/DOCX/PPTX/MD/etc., local or API LLMs, Ollama-friendly.
- **RAGFlow** — heavier-duty, layout-aware parsing (DeepDoc), hybrid retrieval, cites the exact paragraph it pulled from.
- **Kotaemon (Cinnamon)** — Gradio UI, hybrid full-text + vector retrieval, multi-modal doc QA with citations, local or API models.
- **Danswer/Onyx**, **Quivr**, **Khoj** — similar "personal knowledge assistant" tools, some with connectors beyond local files (Notion, Drive, Slack).
- **OpenDocuments** and **watat83/document-chat-system** — newer, broader-format parsers (PPTX, XLSX, Jupyter, code, etc.) with MCP server support, so an agent like Claude Code, Cursor, or Windsurf can search your indexed corpus while assisting with development.
- **miniR** — lighter-weight, retrieval-only (no LLM baked in), just gives you a clean `/retrieve` API to bolt onto whatever agent you want — closer to a build-your-own-layer if you want control.

---

## TURN 2 — Deeper technical questions (dictated)

> No. No. No. No. Let's talk about deeper on this thing. What all of this already existing open source projects contain? Like, I want to learn more about that. Anything I let them... which contains open web UI plus rag, actually, that's the thing that I want. It points and does anything. Well, I'm friendly. Okay. So is it like a overlay? Is it like a JavaScript level? Is there a voice interface within there? That's the question. Rag flow, heavier duty. What is the heavier duty means? It means, like, it can do very big file compilation, something like that. Layout of your person. What's that? Deep doc. What is this thing? Like, explain those things, man. Sites the exact paragraph it pull from. Yeah. Good. That's a thing. But I don't want something like that because citing everything, that's a thing. But I want a Jarvis, which will tell only what is necessary for us to hear. Cotton moon or cinnamon. Okay. Where gradio UI means what is that? Multimodal. That's a thing. Because even if it is images or anything else, it needs to pull up. even if it is video. I need to have that one pulled up. Good thing to know. I need it to be multimodal. Any models, whatever it is, I want a bad model. That's a good thing. Right? But citations... what's that citation mean? I want to tell me about that. Personal knowledge assistant tools with some connectors. Okay. So beyond log and files, there access to Notions, Slack, Drive, those things. I want to connect with the obsidian. You know, not taking app so that we do one embedding and keep it there. And if we want, we can come back. And if the user wants to delete the informations, she can delete. Basically, any LLM is simply someone who can do the work of having any documents, get it known, and if a user ask any kind of question, it can be answered. Whatever it is, if the document contains, then it will answer. If it doesn't, it doesn't doesn't have this thing. Should I add something like this? Like, it's a mix of things I have. File manipulation, file opening, everything, and also file adding like a writer. which I will decide later. But for now, I want to concise my scope, which is any LLM... not any LLM, any rank. So any documents, whatever I... if I have pointing it out, it can do the rank model structure pretty well. Semantic understanding and giving me the context to what I mean. Like, that's good enough. Open documents. What's the thing? You are broader format. It can do many persons. Wow. That's a good one. I might needed the parts or the Indian detection, Indian note, indent in... and detection. So it might be good enough to have that one. Mini r. It's a lighter weight, vertebral only, which means it will be only containing the embeddings. Right? So one thing that I want to do is I want to search all these things, understand what it has over everything. And then I want to have the code base of these things so that I can have them Whatever the things that I want, I can replicate or take it out from there. Like, stealing them from... like, you know, I want those things.

### Response

Going through your questions in order:

**Open WebUI + RAG — is it an overlay, JS-level, voice interface?**
It's a full self-hosted web app (Python backend, Svelte frontend) — not a JS overlay on someone else's tool. It runs its own server, and RAG is a built-in module: you upload docs or point it at folders, it embeds into one of 9 supported vector DBs, and injects retrieved chunks into the prompt at chat time. It confirmed does have voice — integrated voice and video calls with multiple speech-to-text providers (Local Whisper, OpenAI, Deepgram, Azure) and text-to-speech engines (Azure, ElevenLabs, OpenAI, Transformers, WebAPI). So yes, actual mic-in/voice-out, not a gimmick. It's also moving toward "agentic RAG" — instead of always pre-injecting chunks, the model gets shell-like tools (ls, grep, cat) over your knowledge base and decides what to pull when it needs it. That's closer to your Jarvis framing than static injection.

**RAGFlow — what does "heavier duty" mean?**
It means more infrastructure and more parsing sophistication, not just bigger file support. RAGFlow needs 5 services running (app, MySQL, Redis, MinIO, Elasticsearch) instead of one. "Layout-aware" / DeepDoc means it doesn't just dump raw text out of a PDF — it understands the document's visual structure: this text is a table cell, this is a header, this spans two columns. That matters a lot for messy PDFs with tables; a naive text-dump chunker mangles tables, DeepDoc preserves them. It's overkill if your docs are mostly clean markdown/text.

**Citations — what it is, and why your instinct is fine**
"Cites the exact paragraph" means the answer comes with a footnote/link back to the source chunk, so you can verify it wasn't hallucinated. It's a good trust feature, but it's a **UI/prompt setting**, not a structural requirement — every one of these tools can retrieve without surfacing citations in the visible answer. You want the retrieval to happen (that's non-negotiable in RAG — it has to find and pull the right chunk to answer accurately) but you can suppress the "here's exactly where I got this" display and just get the clean Jarvis-style answer. That's a prompt/config choice, not a different architecture.

**Kotaemon — Gradio, multimodal**
Gradio is a Python library for building a web UI without writing frontend code — you write Python, it renders a browser UI. So Kotaemon's "UI" is Python-generated, easy to hack on if you know Python, less flexible than a hand-built React frontend. "Multimodal QA" here means it can retrieve and reason over figures/tables embedded in documents (charts inside a PDF, images inside a slide deck) — not full video understanding. None of the tools found do native video RAG; if that's needed, a separate video-to-text/transcript step before it ever hits the RAG pipeline would be required.

**Connectors + Obsidian**
Notion/Slack/Drive "connectors" just mean the tool has code to pull files from those APIs automatically instead of manual upload. Obsidian isn't usually listed as a "connector" in the bigger tools because it doesn't need to be — an Obsidian vault is just a folder of markdown files, so any tool with folder-watching + markdown ingestion works on it directly. But there's also a whole ecosystem of Obsidian-native plugins doing exactly this spec already: **Analogy** (local ChromaDB + semantic search + exposes an MCP server so external AI tools can query the vault), **Mini-RAG**, **obsidian-rag** (badvision), and **obsidian-notes-rag** (sqlite-vec, MCP server, CLI). Delete-ability is standard — it's just deleting rows/vectors tied to that file's ID, every one of these supports it.

**OpenDocuments — "PII redaction," not "Indian detection"**
Interpreted mis-transcription as **PII redaction** (Personally Identifiable Information) — it strips or masks sensitive personal data before indexing.

**miniR — confirmed correct.** Retrieval-only: ingests, chunks, embeds, gives a `/retrieve` API returning matched text chunks. Deliberately does *not* call an LLM.

**On "stealing" code from these repos**
Check licenses before lifting code:
- Kotaemon, RAGFlow, miniR, most Obsidian plugins -> permissive (Apache/MIT-style), reuse freely.
- Open WebUI -> has commercial-use restrictions in its license beyond a certain scale, worth reading before basing a product on it.

---

## TURN 3 — Full requirements spec (dictated)

> Yeah. I don't want to use the open gateway because I'm not having a UI kind of like that. It's a very simple PyQT UI itself, so I don't think it will be having a problem with that one. So I will tell you exactly what I want, and I want you to go through and compare with whatever it is present and what they have so that we can confirm with the the things that I want to have, and we will pull everything that is relevant to it, and I will configure everything that is needed to have. So let me tell you the exact way I want. The use case is my file explorer. My file system will contain every single files. but I will restrict it. Like, there exist a necessity for that because I don't want to touch any system files or anything. Just simply having the user files, like, user defined files. Right? Direct system for that, documents, for downloads, photos, pictures, videos, those kind of simple files. I want to give there only, like, restriction the flow or the control over. So these folders, which will contain everything that is necessary for it. Then if I drag and drop into this thing, which is the NERAG, it will be able to do the work of embedding this thing. But now I will ask another question. If I v one, like, whatever files or documents I download, I have it locally, I will be able to have this rag pointed to that. That's what I want. Okay. I don't care about anything else. Only thing is I need to download or keep it as locally as possible. Then only I can use this agent or else I can't use. So that's the part there. You can see what I want as a requirement. Then I want any kind of document formats, like, not document itself, any formats. I want to have a lookup through. Images I need. I don't know if it can happen. Like, VLMs or even the videos. I don't know. Maybe. Images and videos, you can skip about that. But, otherwise, I want clearly others to be having the power of using as that rack. So any kind of other document formats I need to able to do that. And I want you to tell me what is the way they I've been doing. Like, they might be using some kind of way. Right? If it is PPT, then they might be converting into to markdown document because there access simply slides only or maybe images, then having an OCR pull up so that the text can be extracted or VLMs. I don't know. You need to tell me exactly what is there or how it is captured and what about the tables inside the PDF. They are using something about that one also. Right? So any kind of documents which will contain images or PDFs, it needs to be rendered and it needs to be taken out so that I can use them for my purpose. I need a embedding or a semantic understanding or any documents, whatever it contains. Images, tables, headers, any kind of things. I need to extract those text and as a semantic understanding for that. This is what I want as a requirement. So you got the understanding on that one. Now coming to the other point, which will be like, let me think. Whatever it might be. Okay. The documents that I uploaded and having the embeddings done, it will be having an understanding about it. Right? Like, the complete embedding is done. Now there should be a database for this thing, embedding story. The mini LLM you mean, like, I don't know the correct name of it, but their existing embedding model, which is, like, AT and B, which will be used for embedding. And vector database, chroma DB. Right? I can use those things. So no worries on those part. Now coming to the other part, which is, like, a cleaning purpose itself. If I use a document and I use the database and have the embeddings done, and if I use that for searching and doing my retrieval process, talking with the LLM. And after that, I don't want to have it. Then I will be doing one thing. I need to clean the database with everything. So those embeddings needed to be gone. And whatever the things that we have at a conversation, I am thinking about storing it inside of the obsidian. But is that a good thing? I think it is a bad idea because it will exceed the storage limit faster, and embeddings should not be present in a database and not database inside the folders. It should be present in a data base. Embedded should be there only. I can't pull and keep it inside the folders. So for that reason, the thing that I want is... I don't know. Maybe simply having the rag itself is good enough, pulling a document, having it, and going against it, and good. But now comes the other specification that I want. I want to pull another document. Meanwhile, pulling another document itself. Like, having both of documents. I don't want to read one and have it detect talking with. Like, I want another document also pulled up. So if I have to come back both documents, I can use it against, like, semantic understanding. Like, we can have something like a comparison. I think there exist, like, string matching, semantic matching, some kind of function there will be right so that I can use to compare two files and understand what's the semantic understanding. Yeah. But still, I want to understand. Right? So for that reason, it's kind of like a ChatGPT, but it is locally done. And mainly, it is for comparison You can say. It's what I want as a ChatGPT. I don't know why I did this thing. Normally, we can do this thing by uploading it into the ChatGPT or Claude and asking for what it contains. But why I am doing this thing, let me think. What's the purpose of this thing? Any rag, any doc rather than pulling up ChatGPT, I have this thing locally. Like, no. I don't know the answer for the question, but it's a part I want. Like, it is something that that I want in my very big environment. The ecosystem that I'm building, this is a part it should have. That's why I thought of this thing. But I am creating it as a separate layer. But even though creating it as a separate layer is bullshit because we have ChatGPT. So it's not a stand alone kind of thing. It's just a library or some kind of a function. This whole project is a function for another big ecosystem that I want. Yeah. Because this project is completely what we have already. ChatGPT, Claude, they can do this thing. Right? So we are just replicating that, having it as a overlay. Now... okay. It's good enough for me, but the thing that I want is I need two other things, which is API connection and also locally running. So if I want a simple locally running thing, it should be like simple. But for API connections, it will be probably... like, I want a Reindexing of the personal details, sometimes there might be inside the documents. Right? So I don't want to give them to the API connections also. So for now, I want to create a local model way of doing. Later, I will create about the API connection. So completely, you do know what I want now, the requirements and everything. And I want you to pull up on the GitHub's repository, which contains these things. They might have already done these things what I have wanted, and I want to relevantly pull all those things and steal them and compile them together and accumulate in a very current target example. Right? So, like, the architecture we will build

### Response

That all makes sense — and yeah, dropping the full-UI idea is right, since you already have PyQt. What you're describing is a **local ingestion + retrieval library**, not an app. Here's the requirement mapping:

**1. Folder scope restriction**
Not something to borrow from a repo — it's just a config allow-list in your own ingestion code (e.g. `~/Documents`, `~/Downloads`, `~/Pictures`, `~/Videos` only, block system paths). Drag-and-drop just triggers your ingestion function on the dropped path.

**2. Extraction pipeline — the actual answer to "how do they do it"**
The library everyone's converging on for this is **Docling** (IBM, MIT license, local, no cloud calls). Here's what it actually does per format:
- **PPTX** -> a layout model classifies each slide region (title, body, table, image placeholder) and pulls text/tables directly from the slide XML — no OCR needed unless a slide is literally a scanned image.
- **PDF tables** -> a dedicated model called **TableFormer** reconstructs the table's actual cell structure (merged cells, multi-row headers) instead of just linearizing rows into flat text.
- **Scanned pages/images with text** -> OCR (EasyOCR or Tesseract, both local) runs *only on the regions the layout model flags as text*, not blindly across the whole page.
- Everything exports to one clean Markdown/JSON format regardless of input type.

**3. Embedding + vector DB**
ChromaDB for storage, and any local sentence-transformer embedding model (bge-small, e5-small, or nomic-embed-text via Ollama). Two `pip install`s and ten lines of code — doesn't need "stealing" from a repo.

**4. Cleanup requirement**
Pattern to copy from Open WebUI: it exposes a File Manager where deleting a source file **automatically cascades and deletes its corresponding embeddings** from the vector store. Index by source-file-path as the metadata key on every chunk, and "forget this doc" becomes one filtered delete against Chroma.

**5. Conversation storage — instinct confirmed right, don't use Obsidian for it.** Embeddings belong in a vector database, not scattered as files in a vault. If any session history is wanted at all, a lightweight local SQLite table (or nothing — ephemeral sessions cleared with the doc) fits the "clean when done" workflow better than a growing vault.

**6. Two-document comparison — needs a different retrieval shape**
Single-doc QA is one query -> one collection -> top-k chunks. Comparison is different: keep each document as its **own separate Chroma collection**, then either:
- retrieve top-k from *both* collections for the user's question and hand both sets to the LLM with a compare/contrast prompt, or
- do an actual **semantic diff**: for every chunk in doc A, find its nearest-neighbor chunk in doc B by cosine similarity, then surface the pairs with *low* similarity (real divergence) and *high* similarity (redundant/overlapping content) separately.

Reference implementation: `AKSHAYINDIA05/Document_Comparison_System` on GitHub does chunk-and-embed-both, retrieve-and-compare — built on Azure, but the retrieval logic is what to lift and rewire to Chroma/Ollama.

**7. "This is just a library, not standalone" — correct, and fine.** It slots in as a component the documentation-agent ecosystem calls into, same role Ollama's `qwen2.5:7b-instruct-q4_K_M` already plays there.

**8. Local-first now, API later**
Structure the LLM call and the embedding call behind one interface with two backends (local Ollama / remote API) from day one, even if only the local one gets wired up now — the exact abstraction Open WebUI uses to swap Ollama <-> OpenAI-compatible endpoints.

---

## TURN 4 — Correction: two personas, API reconsideration (dictated)

> That's why you didn't correctly get it. I want two guys, two Jarvis, not actual Jarvis. I will name another guy. It's a small subset of Jarvis where two of these peoples will be helping me with. Like, I will have the LLM talk in a way. That's another part which we will discuss later, but two LLMs will be present and both of them can do the work of having talking with me. and I might consider having an API because I don't want to have a local. Because it will be tough to do this thing. And if the document is good enough to upload as an API key, not API key, not API connection. I will be using it as API. I won't be running a local. But it's kind of like this. Okay? used ChatGPT and Claude to do this work. Like, primarily understanding a document or completely getting what it is. So if I have this thing, then there is no need for this thing, or ChatGPT or Claude. I will be simply having this thing run, and it talks to me also, so no worries about it. So you know what I am trying to say. I'm trying to build a people which is specialized over my document, and they will talk to me and understand what that document contains, and they will make me understand. kind of like that way. That's the philosophy that I'm trying to tackle.

### Response

Got it — now it clicks. Not a diff algorithm, two personas. Each document gets its own specialized conversational agent grounded in its content — a "mini-Jarvis" per doc — and you talk to each one directly, and it explains its document to you in natural conversation rather than you reading a comparison report. If you want an actual comparison between the two, that'd happen by you asking one agent about the other's territory, or asking both the same question and hearing how their answers differ — not a background similarity computation. That's a much simpler retrieval shape than what was described before: one persona + one document's context per agent, standard single-doc RAG, just running two of them.

---

## TURN 5 — GPU/VRAM question (dictated)

> Seven b class model. Tell me about my model or not model. My GPU. Thirty fifty four GPU V RAM trying to run a seven b to retrieve one query and having, like, a talkable human being, you can tell me exactly what I trying to say.

### Response

Direct answer: on a 4GB VRAM card, a 7B model is tight even before RAG comes into play.

**The math:** Q4_K_M quantization of a 7B model runs about 4.1–4.4GB just for weights. That's already at or over the VRAM ceiling with nothing left for the context window or KV cache. Ollama will auto-split layers between GPU and CPU when it doesn't fit — which it will do here — and that CPU spillover is where "talkable" dies. Fully-on-GPU 7B feels like a real conversation (~20-30 tok/s). Partially-offloaded 7B on a 3050 realistically drops to 2-5 tok/s. That's not chat, that's watching a sentence get typed out slowly.

RAG makes this worse, not better: retrieved chunks get injected into every prompt (Open WebUI's own defaults are ~5,000 tokens of context per turn), so it's not just decoding a short reply — it's processing a long prefill every single query. More latency stacked on top of the offload slowdown.

**Already answered by prior project data.** The documentation-agent project runs on this exact same 3050, and already landed on `qwen2.5:7b-instruct-q4_K_M` with `llama3.2:3b` as a fallback — that fallback exists precisely because the 7B isn't reliably snappy on this hardware.

---

## TURN 6 — Pushback on quality/speed tradeoff (dictated)

> I want the responses paid, but the thing is reasoning quality will improve if I improve that model also. Because there exist multiple models which is capable of doing those things. So I don't believe in... like, it's not hand in hand. Reasoning quality and responses paid, both of them can increase drastically.

### Response

You're half right, and the earlier framing needed correcting — but not folding entirely.

**What's right:** model efficiency has genuinely improved, so "quality" and "speed" aren't locked to each other the way they were a year or two ago. Newer architectures mean a well-built 3-4B model today can out-reason older 7-13B models while running faster. Concretely for this GPU: **Phi-4-mini (3.8B, MIT license, 128K context)** is built specifically for constrained hardware and benchmarks close to models twice its size on math/reasoning. That's a straight upgrade over the current llama3.2:3b fallback — same speed class, sharper reasoning — with no tradeoff.

---

## TURN 7 — Reference Repositories & Markdown File Request (dictated)

> Okay. Anyway, uh, coming to the part of local five model, you can keep that, uh, PHI. Okay? Good enough. For now, let's leave on that part. API, local. Don't worry about those things. I want to come to the part where we need to talk about that agent we are trying to create and the GitHub repositories, which we need to pull and what are the relevant things which I want is already present with theirs, and I want to steal those things and keep it inside and compile them and completely accumulate everything necessary for the reference and getting it for doing one thing. the job that I just mentioned about, the use case. I want to clearly log in on that, and I want you to create a very detailed accumulated session history markdown file containing everything which I just mentioned about so that we can use that one. And I want you to have every link for the reference which we will be needing for the GitHub repositories, all of those things. and every single conversation on the problems and statements. I want you to pull everything. No summarization, no rewriting, everything as it is. Keep it inside that markdown file.

---

## REFERENCE LINKS — All URLs Surfaced Across Sessions

### RAG / Document-Chat Platforms
- https://github.com/joungminsung/OpenDocuments
- https://railway.com/deploy/ragflow-rag-engine (RAGFlow)
- https://billtcheng2013.medium.com/open-source-rag-based-chat-ui-e393eafbfd23
- https://github.com/ntluong95/document-RAG
- https://github.com/yaacov/rag-chat-interface
- https://github.com/ben0724-ACE/mini-rag
- https://www.tauceti.blog/posts/turn-your-computer-into-ai-machine-chat-with-your-documents-rag/
- https://github.com/watat83/document-chat-system
- https://www.github.com/billy-enrizky/chat-with-documents
- https://github.com/Cinnamon/kotaemon

### Open WebUI
- https://github.com/open-webui/open-webui
- https://huggingface.co/mexicanamerican/openweb-ui
- https://insiderllm.com/guides/open-webui-setup-guide/
- https://github.com/limccn/rag-web-ui
- https://docs.openwebui.com/troubleshooting/rag/
- https://docs.openwebui.com/features/chat-conversations/rag/
- https://exa.ai/integrations/open-webui
- https://github.com/rag-web-ui/rag-web-ui
- https://docs.openwebui.com/features/

### Obsidian RAG Plugins/Tools
- https://community.obsidian.md/plugins/analogy-rag-in-your-vault
- https://community.obsidian.md/plugins/mini-rag
- https://motherduck.com/blog/obsidian-rag-duckdb-motherduck/
- https://community.obsidian.md/plugins/rag-chat
- https://github.com/badvision/obsidian-rag
- https://community.obsidian.md/plugins/local-llm-hub
- https://pypi.org/project/OBRAG/
- https://github.com/proofsh/obsidian-notes-rag
- https://github.com/robmadole/obsidian-brain

### Document Extraction / Parsing
- https://www.greptile.com/grepository/docling
- https://apify.com/raional/pdf-to-markdown-converter.md
- https://stat.ethz.ch/CRAN/web/packages/doclingr/index.html
- https://arxiv.org/pdf/2508.15817
- https://medium.com/@sanikachavan1806/docling-is-quietly-changing-how-we-build-ai-document-pipelines-4ee9e6f57164
- https://docling.org/

### Document Comparison / Semantic Diff
- https://github.com/AKSHAYINDIA05/Document_Comparison_System
- https://github.com/topics/document-comparison
- https://github.com/GiovanniPasq/chunky
- https://github.com/topics/document-similarity?o=asc&s=forks
- https://github.com/NayeemAhsan/LLM-Powered-RAG-based-Document-Comparison-Tool

---
---

# PART 2: Chronological Codebase Changelog

Every modification, architectural decision, and tool interaction recorded chronologically with exact timestamps.

---

### [2026-09-11 13:41:15 IST] — Initial Requirements Discovery & Environment Inspection
- **Action**: Inspected session log and pre-downloaded embedding model directory `models/embeddings/all-MiniLM-L6-v2`.
- **Findings**:
  - Offline, format-agnostic document ingestion and retrieval system ("AnyRAG") acting as a personal Jarvis layer.
  - Documents to support: PDF (including tables), DOCX, PPTX (slides & notes), Markdown, and Plain Text.
  - Identified requirement for folder restrictions (blocking `C:\Windows`, `C:\Program Files`, etc.).
  - Identified requirement for cascade cleanup (deleting a file must purge all its vector embeddings).
  - Identified "Two Jarvis" requirement: grounded document personas and cross-document comparison / semantic diff.
  - Verified local embedding model `all-MiniLM-L6-v2` was fully pre-downloaded (384-dimensional `model.safetensors`).
- **Environment Checks**:
  - Python version: `Python 3.10.11`
  - Git version: `git 2.53.0.windows.1`
  - Package ecosystem: `PyMuPDF 1.27.2.2`, `python-docx 1.2.0`, `python-pptx 1.0.2`, `sentence-transformers 6.0.0`, `torch 2.10.0+cu128`.

---

### [2026-09-11 13:44:46 IST] — Formulation of Implementation Plan
- **Action**: Authored `implementation_plan.md` detailing architecture, security guardrails, multi-format parsers, offline vector store, dual-persona comparator, and CLI/PyQt priorities.
- **Feedback Received (13:45:19 IST)**: User requested prioritizing the core library, repo pulling, and comparison engine, while deferring the PyQt GUI for later.
- **Plan Update (13:45:23 IST)**: Refactored implementation plan to prioritize core headless engine and CLI.

---

### [2026-09-11 13:45:39 IST] — Reference Open-Source Repositories Cloned into `repo/`
- **Action**: Pulled top 4 open-source reference implementations into `c:/Users/iqand/Downloads/ANYRAG/repo/`:
  1. `repo/mini-rag`: Fast, minimal retrieval-only pattern.
  2. `repo/OpenDocuments`: Multi-format parsing and privacy/agent concepts.
  3. `repo/Document_Comparison_System`: Cross-document comparison patterns.
  4. `repo/chunky`: Layout-aware text chunking algorithms.

---

### [2026-09-11 13:46:08 IST – 13:48:43 IST] — Core AnyRAG Engine Architecture Implemented
- **Package Created**: `anyrag/`
  - **`anyrag/config.py` (13:46:14 IST)**:
    - Defined default data and model paths.
    - Added `is_path_allowed()` guardrail blocking `C:\Windows`, `C:\Program Files`, `C:\ProgramData`, etc.
  - **`anyrag/parsers/` (13:46:21 – 13:46:55 IST)**:
    - `base.py`: `ExtractedDocument` and `ExtractedSection` data models with deterministic ID hashing.
    - `pdf_parser.py`: PyMuPDF (`fitz`) parser extracting text blocks and markdown tables.
    - `docx_parser.py`: `python-docx` parser extracting paragraphs, heading hierarchy, and tables.
    - `pptx_parser.py`: `python-pptx` parser extracting slides, body text, speaker notes, and tables.
    - `text_parser.py`: Markdown and plain text parser with header-level splitting.
    - `registry.py`: Universal parser router enforcing folder scope security.
  - **`anyrag/chunking/` (13:47:03 – 13:47:10 IST)**:
    - `chunker.py`: Recursive character chunker with contextual prefixes and table structure preservation.
  - **`anyrag/embeddings/` (13:47:15 – 13:47:19 IST)**:
    - `embedder.py`: Local `SentenceTransformer` loader connecting exclusively to `models/embeddings/all-MiniLM-L6-v2` (100% offline, 384 dimensions).
  - **`anyrag/storage/` (13:47:39 – 13:47:44 IST)**:
    - `vector_store.py`: Embedded SQLite database storing chunk texts, metadata, and normalized float32 vector blobs. Implemented cosine similarity search and `purge_document()` with atomic cascade deletion.
  - **`anyrag/agents/` (13:47:54 – 13:48:16 IST)**:
    - `llm_client.py`: Unified client supporting local Ollama, OpenAI-compatible APIs, and an intelligent offline extractive synthesis engine.
    - `persona.py`: `DocumentPersona` grounded single-document Jarvis agent.
    - `comparator.py`: `DocumentComparator` enabling cross-document contrast and chunk-level **semantic diff**.
  - **`anyrag/engine.py` (13:48:24 IST)**:
    - High-level coordinator unifying ingest, ask, compare, diff, list, search, and purge.
  - **`anyrag/cli.py` & `main.py` (13:48:34 – 13:48:38 IST)**:
    - User-friendly CLI with subcommands: `ingest`, `list`, `ask`, `compare`, `diff`, `search`, `purge`, `clear`.
  - **`requirements.txt` (13:48:43 IST)**:
    - Pinned essential core library dependencies.

---

### [2026-09-11 13:48:52 IST – 13:50:23 IST] — End-to-End Automated Testing & Optimization
- **Test Suite**: `tests/test_anyrag.py`
  - Validated clean slate database creation.
  - Ingested real 249-line session log (90 chunks generated & embedded).
  - Generated and ingested sample DOCX and PPTX documents.
  - Tested Single-Document Persona ("Doc Jarvis") Q&A.
  - Tested Cross-Document comparison and chunk-level semantic diff.
  - Fixed Windows console CP1252 encoding output (replacing Unicode checkmarks with ASCII `[PASS]`).
  - Fixed `purge_document()` in `vector_store.py` to match filenames directly.
  - Verified 100% test pass: `=== ALL ANYRAG TESTS PASSED SUCCESSFULLY! ===`.

---

### [2026-09-11 13:50:43 IST – 13:52:00 IST] — Performance Polish & CLI Verification
- **`anyrag/engine.py`**:
  - Implemented lazy loading for the embedding model property. Non-vector commands (like `main.py list` and `main.py purge`) now start instantly without loading heavy PyTorch weights.
- **`anyrag/cli.py`**:
  - Sanitized bullet characters to standard ASCII hyphens (`-`) for clean display across all Windows command shells.
- **Documentation**:
  - Generated initial `README.md` and `walkthrough.md`.

---

### [2026-09-11 13:54:15 IST – 13:55:00 IST] — Workspace Organization & Cleanup
- **Deleted Folder**: Removed `tests/` folder as requested by the user.
- **Cleaned Data Directory**: Purged temporary testing artifacts (`data/sample_hardware.docx`, `data/sample_presentation.pptx`), keeping only the persistent SQLite vector database `data/anyrag_vectors.db`.
- **Refactored `README.md`**: Simplified and aligned strictly with core philosophy, use case, and 3-command CLI guide.

---

### [2026-09-11 13:56:45 IST] — Consolidation into Unified `docs/CHANGELOG.md` & Folder De-duplication
- **Eliminated Duplicate Folder**: Removed duplicate `doc/` directory to standardize completely on `docs/`.
- **Unified Document**: Merged the full verbatim **Session Log (Part 1)** and the **Time-stamped Codebase Changelog (Part 2)** into this single definitive file at `docs/CHANGELOG.md`.
- **Updated Project References**: Updated `README.md` file links to point cleanly to `docs/CHANGELOG.md`.

---

### [2026-09-11 13:58:35 IST] — Streamlined README to Pure Use Case & Philosophy
- **Removed Command Walkthrough**: Stripped out the CLI commands tutorial block from `README.md` to fulfill the directive of keeping the document purely focused on the project's purpose and foundational philosophy.

---

### [2026-09-11 14:00:15 IST] — LLM Client Model Auto-Detection & Initial Tuning
- **Auto-Detection**: Updated `anyrag/agents/llm_client.py` to query local Ollama's `/api/tags` to automatically discover and bind installed local models.
- **Model Discoveries**: Identified local models in Ollama manifests, establishing baseline local inference connection.

---

### [2026-09-11 14:05:40 IST] — Local Phi-4-Mini Abliterated GGUF Integration
- **Asset Discovery**: Located user's local `assets/models/phi-4-mini-[3.8b-q4_k_m]-abliterated.gguf` (2.49 GB) and `assets/embeddings/all-MiniLM-L6-v2`.
- **Modelfile Creation**: Authored `assets/models/Modelfile` linking directly to the local GGUF weights.
- **Ollama Ingestion**: Launched local Ollama server and executed `ollama create phi4-mini -f Modelfile`, successfully creating `phi4-mini:latest`.
- **GPU Acceleration**: Verified Ollama runtime offloaded all 33/33 layers onto the NVIDIA GeForce RTX 3050 Laptop GPU (`CUDA0`), utilizing 2368 MiB model buffer and 512 MiB KV cache with Flash Attention enabled.
- **Path Tuning**: Updated `anyrag/config.py` to dynamically prioritize `assets/embeddings/all-MiniLM-L6-v2`.

---

### [2026-09-11 14:10:30 IST] — Standalone `llama.cpp` Runtime Setup & Direct Verification
- **Binary Extraction**: Located prebuilt `llama.cpp` CUDA binaries on system and copied them to `assets/runtime/` (`llama-cli.exe`, `ggml-cuda.dll`, `llama.dll`, `ggml.dll`, `libomp.dll`).
- **Direct Standalone Testing**: Ran `assets/runtime/llama-cli.exe -m assets/models/phi-4-mini-[3.8b-q4_k_m]-abliterated.gguf` directly without Ollama.
- **Performance Verification**: Successfully generated response *"Hello! I'm Phi-4-mini, ready to assist you with your queries."* at **11.6 tokens/second**, confirming direct GGUF execution support.
- **LLM Client Fixes & Polish**:
  - Restored `generate()` method in `anyrag/agents/llm_client.py`.
  - Added explicit `self.api_base` initialization.
  - Set default local model strictly to `phi4-mini`.
  - Increased request timeout to 120s to allow initial 2.5 GB model weights to load smoothly into GPU memory.

---

### [2026-09-11 14:15:30 IST – 14:16:30 IST] — Comprehensive Codebase Audit & Organization
- **Workspace Audit**: Evaluated every file and directory across `ANYRAG/` for necessity and relevance.
- **Organization**:
  - Identified all redundant non-source assets across directories.
  - Purged all compiled `__pycache__` directories across the package.
  - Removed nested `.git` directories inside `repo/` submodules to prevent Git submodule conflicts.
  - Removed bulky non-code demo media files from `repo/` (e.g., `chunky/assets/demo.gif`, saving ~6 MB).
- **Integrity Check**:
  - Verified `python main.py list` successfully loads and displays indexed documents from `data/anyrag_vectors.db`.
  - Confirmed core structure: `anyrag/`, `assets/`, `data/`, `docs/`, `repo/`, `main.py`, `README.md`, `requirements.txt`.

---

### [2026-09-11 14:17:30 IST – 14:18:05 IST] — Ollama Daemon Shutdown & Complete Modelfile Deprecation
- **Background Daemon Terminated**: Cancelled and terminated the running `ollama serve` background process (`task-349`) to completely free the GPU VRAM and release local ports.
- **Modelfile Deprecated & Deleted**:
  - Identified that `Modelfile` is strictly an Ollama packaging recipe for the `ollama create` CLI command.
  - Because AnyRAG is running **standalone llama.cpp** (`assets/runtime/llama-cli.exe`) directly against the raw GGUF file (`assets/models/phi-4-mini-[3.8b-q4_k_m]-abliterated.gguf`), `Modelfile` is 100% obsolete.
  - Completely deleted `Modelfile` from `assets/models/` and root to eliminate all unused configuration clutter.

---

### [2026-09-11 14:21:25 IST – 14:21:45 IST] — Direct Standalone `llama.cpp` Subprocess Integration
- **Configuration Update (`anyrag/config.py`)**:
  - Added explicit constants `DEFAULT_LLAMA_CLI_PATH` pointing to `assets/runtime/llama-cli.exe` and `DEFAULT_GGUF_MODEL_PATH` pointing to `assets/models/phi-4-mini-[3.8b-q4_k_m]-abliterated.gguf`.
- **LLM Client Native Execution (`anyrag/agents/llm_client.py`)**:
  - Upgraded `LLMClient` to prioritize direct, offline execution via `_call_llama_cli()`.
  - Configured prompt formatting matching Phi-4 instruct tags (`<|system|>...<|end|><|user|>...<|end|><|assistant|>`).
  - Added `-ngl 33` for GPU layer offloading directly to CUDA, `--simple-io`, `--no-display-prompt`, and `stdin=subprocess.DEVNULL` to run non-interactively without background services.
  - Established automatic fallback chain: Direct `llama.cpp` -> Local Ollama (if active) -> OpenAI-compatible API (if key configured) -> Smart Grounded Extractive Synthesis.

---

### [2026-09-11 14:31:00 IST – 14:33:30 IST] — Database Integrity, Foreign Key Enforcement, Vectorized Comparator & Hygiene
- **Database Re-Ingestion Stale Duplicate Fix (`anyrag/storage/vector_store.py`)**:
  - Identified and fixed root cause where editing and re-ingesting a document orphaned stale entries in `documents` and duplicated chunks in `chunks`. Since `ExtractedDocument.generate_id` calculates a SHA256 content hash, file modifications generate a fresh `doc_id`, bypassing the old `DELETE WHERE doc_id = ?` check.
  - Updated `add_document_and_chunks()` to query `WHERE file_path = ? OR doc_id = ?` and cleanly purge prior records and vectors before inserting updated document data.
  - Purged the pre-existing duplicate record (`fa0c19ae6ce72169`, 95 chunks) from `data/anyrag_vectors.db`, keeping only the current version (`f50ffc3d361b02e9`, 104 chunks).
- **Active SQLite Foreign Key Enforcement (`anyrag/storage/vector_store.py`)**:
  - Enabled `PRAGMA foreign_keys = ON;` in `_get_conn()`, activating SQLite's engine-level enforcement of the `FOREIGN KEY (doc_id) REFERENCES documents (doc_id) ON DELETE CASCADE` constraint on the `chunks` table.
  - Updated `purge_document()` to use `cursor.fetchall()` so all matching rows are cleanly cascaded and removed.
- **Vectorized Semantic Diff Matrix (`anyrag/agents/comparator.py`)**:
  - Replaced the $O(N \times M)$ nested Python `for` loop and scalar `np.dot` calculations in `DocumentComparator.compute_semantic_diff()` with vectorized BLAS matrix multiplication (`np.matmul` on L2-normalized embedding matrices).
- **Repository Hygiene & `.gitignore`**:
  - Authored a comprehensive root `.gitignore` ignoring Python bytecode (`__pycache__/`, `*.py[cod]`), SQLite databases (`data/*.db`, `*.sqlite*`), virtual environments (`.venv/`, `venv/`), environment files (`.env*`), and IDE metadata.
  - Purged compiled `__pycache__/` directories from the project tree.

---

### [2026-09-11 20:25:00 IST – 20:28:30 IST] — Docling Parser Error Validation, Lazy Import Optimization & Robustness Hardening
- **Logic Bug Resolution (`anyrag/parsers/docling_parser.py`)**:
  - Identified and fixed `metadata["has_complex_tables"]` miscalculation. The prior implementation checked `len(sections) > 0`, which was guaranteed to be `True` for any document because `full_markdown` text was appended to `sections`.
  - Added dedicated counting for table sections (`table_count = sum(1 for s in sections if s.section_type == "table")`), correctly populating `has_complex_tables = table_count > 0` and recording `tables_count`.
- **Import Performance & Lazy Loading (~40x Module Load Speedup)**:
  - Eliminated eager top-level `from docling.document_converter import DocumentConverter` which forced Python to initialize PyTorch, HuggingFace transformers, and OCR dependencies on every import of `anyrag.parsers`.
  - Replaced with fast spec check (`is_docling_available()` via `importlib.util.find_spec("docling")`), reducing import latency from ~15–20s down to ~0.47s.
  - Moved heavy `DocumentConverter` import into `_get_converter()` so it is only loaded on-demand when parsing is actively triggered.
  - Preserved backward compatibility with `HAS_DOCLING = is_docling_available()`.
- **Path Resolution & Validation**:
  - Expanded parameter typing to `Union[str, Path]`.
  - Standardized on `file_path = Path(file_path).resolve()` and added explicit `if not file_path.exists(): raise FileNotFoundError(...)` to prevent `AttributeError` and runtime panics.
- **Table Page Provenance Extraction**:
  - Extracted `page_no` from Docling's `table.prov` (`ProvenanceItem.page_no`) and populated `page_number` on each table `ExtractedSection`, ensuring alignment with `PDFParser`.
- **Empty Content Filtering & Fallback `raw_text`**:
  - Added empty/whitespace guarding on extracted tables to avoid inserting empty table sections.
  - Enhanced `raw_text` to fall back to concatenated section text if document-level `full_markdown` is unavailable or empty.

---

### [2026-09-11 20:30:00 IST – 20:35:00 IST] — Folder Allowlist Rewrite, Dedicated Structured Parsers & ChromaDB Vector Store Migration
- **Folder Allowlist Rewrite (`anyrag/config.py`)**:
  - Replaced legacy system path denylist with a strict folder allowlist guardrail.
  - Ingestion is now restricted strictly to `Documents`, `Downloads`, `Pictures`, and `Videos` (and their subfolders) under the user home profile, automatically resolving OneDrive mirrored variants.
  - Rejected by default: `C:\Windows`, `C:\Program Files`, `Desktop`, external drives, and all non-allowlisted folders.
  - Added support for `ANYRAG_ALLOWED_DIRS` environment variable (delimited by `os.pathsep`) to support customizable allowlist roots for tests and server environments.
  - Updated `is_path_allowed()` and `ParserRegistry.parse()` to emit descriptive `PermissionError` messages explaining allowed directory boundaries.
- **Dedicated Structured Parsers (`anyrag/parsers/`)**:
  - Replaced flat `TextParser` fallbacks for tabular, structured, code, and web document formats:
    - **`CSVParser` (`anyrag/parsers/csv_parser.py`)**: Sniffs delimiters, extracts column headers, and batches data rows (default 15 rows) into formatted Markdown tables with headers repeated on every batch so semantic chunk embeddings retain full column context. Sets `section_type="table"` to engage `RecursiveChunker`'s intact-table preservation logic.
    - **`JSONParser` (`anyrag/parsers/json_parser.py`)**: Decomposes JSON structures into logical sections based on top-level key paths (`Key: <key>`) and groups large arrays into indexed record batches (`Items <start> to <end>`) instead of dumping flat unorganized JSON strings.
    - **`CodeParser` (`anyrag/parsers/code_parser.py`)**: Uses Python `ast` to parse `.py` source code along semantic boundaries. Separates module imports/setup, individual functions (`def`/`async def`), class headers, and class methods into discrete sections. Completely eliminates mid-body function slicing. Provides regex/indentation boundary fallback for non-Python or syntax-broken code.
    - **`HTMLParser` (`anyrag/parsers/html_parser.py`)**: Uses `BeautifulSoup` to strip boilerplate tags (`<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<aside>`, `<noscript>`, `<svg>`, `<form>`). Hierarchically groups content by headings (`<h1>`-`<h6>`), formats lists into Markdown bullets, and converts `<table>` elements into Markdown tables.
    - **`ParserRegistry` (`anyrag/parsers/registry.py`)**: Registered `.csv` -> `CSVParser()`, `.json` -> `JSONParser()`, `.py` -> `CodeParser()`, `.html`/`.htm` -> `HTMLParser()`. Exported all parsers in `anyrag/parsers/__init__.py`.
- **Vector Store Migration: SQLite → ChromaDB (`anyrag/storage/vector_store.py`)**:
  - Migrated vector storage and similarity retrieval from hand-rolled SQLite tables with in-memory linear cosine scanning to ChromaDB's persistent client and collection API.
  - Configured persistent collections in `data/chromadb/`:
    - `anyrag_chunks`: Chunks with HNSW cosine metric indexing (`metadata={"hnsw:space": "cosine"}`).
    - `anyrag_docs`: Document-level metadata catalog.
  - Maintained 100% backward compatibility for all API methods across `AnyRAG` engine, `DocumentPersona`, and `DocumentComparator`:
    - `add_document_and_chunks(doc, chunks, embeddings)`: Atomically upserts document catalog records and chunk vectors.
    - `purge_document(doc_id_or_path)`: Cascade deletion matching `doc_id`, `file_path`, or `file_name`.
    - `similarity_search(query_vector, top_k, doc_ids, min_score)`: Fast HNSW vector search with cosine similarity scoring (`1.0 - distance`), filtering by `min_score` and optional `doc_ids`.
    - `get_all_chunks_for_doc(doc_id)`: Retrieves all chunks with float32 vector arrays for `DocumentComparator` semantic diff matrices.
    - `list_documents()` and `get_document(doc_id)`: Document catalog retrieval sorted by indexing timestamp.
    - `clear_all()`: Resets collections.
  - Added `DEFAULT_CHROMA_DIR = DEFAULT_DATA_DIR / "chromadb"` to `anyrag/config.py` and updated `anyrag/engine.py`.
  - Updated `requirements.txt` with `chromadb>=0.5.0`, `beautifulsoup4>=4.12.0`, and `docling>=2.0.0`.
  - **Stale Pre-Migration Database Deletion & Hygiene**:
    - Permanently purged obsolete `data/anyrag_vectors.db` (750KB legacy SQLite database) following full migration to ChromaDB.
    - Re-pointed `DEFAULT_DB_PATH = DEFAULT_CHROMA_DIR` in `anyrag/config.py` and `anyrag/storage/vector_store.py`.
    - Updated `README.md` architecture specifications and repository layout to reflect persistent ChromaDB storage in `data/chromadb/`.
    - Updated `.gitignore` to explicitly ignore `data/chromadb/`, `*.log`, and temporary files.
    - Purged all compiled `__pycache__/` directories and transient bytecode across the workspace.

---

### [2026-09-11 21:15:00 IST – 21:20:00 IST] — Repository De-Bloat, Hybrid Retrieval (BM25 + Dense RRF) & Dual-Strategy Table Extraction
- **Repository De-Bloat & Debris Purge (`repo/`)**:
  - Permanently deleted the `repo/` directory containing upstream research clones (`OpenDocuments`, `chunky`, `mini-rag`, `Document_Comparison_System`), saving disk footprint and keeping the workspace 100% focused on AnyRAG core.
  - Updated `README.md` repository structure tree to reflect the clean layout.
- **Hybrid Retrieval: BM25 + Dense Embeddings via Reciprocal Rank Fusion (`anyrag/storage/bm25.py` & `anyrag/storage/vector_store.py`)**:
  - Authored a high-performance, self-contained `BM25Index` in pure Python (`anyrag/storage/bm25.py`) using BM25Okapi ($k_1=1.5, b=0.75$) with Robertson-Spärck Jones Inverse Document Frequency (IDF) and inverted index token lookup.
  - Required **zero new external dependencies or background services**, adhering strictly to the "reusable engine, not bloatware" philosophy.
  - Integrated BM25 index synchronization into `VectorStore` on chunk addition, deletion, and hydration.
  - Implemented `VectorStore.hybrid_search()` using standard **Reciprocal Rank Fusion (RRF)**:
    $$\text{Score}(d) = \frac{w_{\text{dense}}}{60 + \text{rank}_{\text{dense}}(d)} + \frac{w_{\text{BM25}}}{60 + \text{rank}_{\text{BM25}}(d)}$$
  - Solves the critical "exact token / keyword blindness" problem of pure dense retrieval (e.g. searching for error codes `0x80070005`, invoice IDs `#INV-2024-9988`, or specific function identifiers `calculate_profit`), while maintaining deep semantic matching for conceptual queries.
  - Wired `hybrid_search()` into `AnyRAG.search_all()`, `DocumentPersona.ask()`, and `DocumentComparator.compare_query()`.
- **Dual-Strategy PDF Table Extraction: Lattice + Stream (`anyrag/parsers/pdf_parser.py`)**:
  - Replaced single-pass table extraction with a dual-strategy heuristic engine in `PDFParser`:
    - **Pass 1 (Lattice)**: Detects structured bordered tables using PyMuPDF vector line analysis (`strategy="lines"`).
    - **Pass 2 (Stream)**: Detects borderless tabular data (e.g. invoices, financial statements) aligned by whitespace columns (`strategy="text"`).
  - Implemented **cell-density validation** ($\ge 35\%$ fill ratio, minimum $2\times 2$ grid) to reject false-positive multi-column text paragraphs.
  - Implemented **spatial de-duplication**: Stream tables overlapping with bounding boxes of already-extracted lattice tables are automatically discarded.
  - Preserves table sections as Markdown tables, keeping them intact during chunking.

---

### [2026-09-11 21:50:00 IST – 21:53:00 IST] — Architecture Refactoring: `anyrag/` → `backend/`
- **Package Reorganization (`anyrag/` → `backend/`)**:
  - Reorganized package directory structure from `anyrag/` to `backend/` to adopt a standard full-stack backend architecture, cleanly isolating core engine services (parsers, chunking, embeddings, storage, agents) from root configuration, documentation, assets, and future UI/frontend components.
- **Import Namespace Migration (`anyrag.*` → `backend.*`)**:
  - Updated entry point in [main.py](file:///c:/Users/iqand/Downloads/ANYRAG/main.py): `from backend.cli import main`.
  - Updated all core backend modules to use the `backend` namespace:
    - `backend/engine.py`: updated imports for `config`, `parsers.registry`, `chunking.chunker`, `embeddings.embedder`, `storage.vector_store`, and `agents`.
    - `backend/cli.py`: updated import to `from backend.engine import AnyRAG`.
    - `backend/chunking/chunker.py`: updated imports to `backend.config` and `backend.parsers.base`.
    - `backend/parsers/registry.py`: updated import to `backend.config`.
    - `backend/parsers/pdf_parser.py`: updated import to `backend.config`.
    - `backend/embeddings/embedder.py`: updated import to `backend.config`.
    - `backend/storage/vector_store.py`: updated imports to `backend.config`, `backend.chunking.chunker`, and `backend.parsers.base`.
    - `backend/agents/persona.py`: updated imports to `backend.storage.vector_store` and `backend.embeddings.embedder`.
    - `backend/agents/llm_client.py`: updated import to `backend.config`.
    - `backend/agents/comparator.py`: updated imports to `backend.storage.vector_store` and `backend.embeddings.embedder`.
- **Documentation & Layout Updates**:
  - Updated [README.md](file:///c:/Users/iqand/Downloads/ANYRAG/README.md) project directory diagram and engine descriptions to reflect `backend/`.
- **Verification**:
  - Verified `python main.py --help` (Exit code 0, all CLI subcommands active).
  - Verified `python main.py list` (Exit code 0, ChromaDB persistent collections loaded and operational without import errors).

---

### [2026-09-20 09:45:00 IST – 10:02:00 IST] — Anti-Hallucination Error Handling, Warm Llama-Server Inference, BM25 Index Persistence & Library Packaging
- **Typed LLM Error Handling (`backend/agents/llm_client.py`)**:
  - Identified critical anti-hallucination leak: `LLMClient.generate()` caught backend exceptions and returned formatted error strings (`[Ollama Error: ...]`, `[llama.cpp Error: ...]`, `[API Error: ...]`). Downstream consumers and document personas treated these strings as legitimate grounded text.
  - Implemented explicit exception hierarchy: `LLMError`, `LLMConnectionError`, and `LLMGenerationError`.
  - Specific provider requests (`ollama`, `llamacpp`, `openai`) now raise typed exceptions immediately on connection or generation failures.
  - In `provider="auto"`, fallback events are logged as warnings via `logging`. If all live providers fail, offline extractive synthesis is used when context chunks exist, or `LLMGenerationError` is raised. No error strings are ever returned as generated answers.
- **Warm `llama-server` Inference Architecture (`backend/agents/llama_server.py` & `backend/agents/llama_server_runner.py`)**:
  - Eliminated per-query `llama-cli.exe` process spawning, which incurred a 15–20s cold load of the ~2.5GB Phi-4-mini GGUF model on every single question.
  - Authored `LlamaServerManager` and `backend.agents.llama_server_runner` which dynamically launch and manage a warm `llama-server` background process using `assets/runtime/llama-server-impl.dll` or `llama-server.exe`.
  - Configured optimized context allocation (`-c 4096`, `-ngl 33`, host `127.0.0.1`, configurable port via `ANYRAG_LLAMA_SERVER_PORT`).
  - Added graceful startup health polling against `/health` and clean process termination hooks via `atexit`.
  - Rewired `LLMClient._call_llama_server()` to send queries to the OpenAI-compatible `/v1/chat/completions` endpoint.
  - **Inference Benchmark**: Query latency dropped from ~15–20 seconds down to **~438 milliseconds** on warm execution.
- **BM25 Index Disk Persistence (`backend/storage/bm25.py` & `backend/storage/vector_store.py`)**:
  - Eliminated quadratic startup penalty in `VectorStore._hydrate_bm25()` which pulled every document chunk from ChromaDB and re-tokenized all text in Python memory on every engine instantiation.
  - Added atomic `save(file_path)` and `load(file_path)` methods to `BM25Index` using `pickle` serialization with atomic `.tmp -> .pkl` renaming.
  - Updated `VectorStore` to persist the sparse index to `bm25_index.pkl` in the ChromaDB directory. Startup checks if the cached index chunk count matches `chunks_col.count()`, achieving **$O(1)$** instant loading without reading chunks from ChromaDB.
  - Synchronized cache updates on document additions (`add_document_and_chunks`), deletions (`purge_document`), and clearing (`clear_all`).
- **Standard Logging & PEP 517/621 Packaging (`pyproject.toml`)**:
  - Replaced internal status `print()` statements across library modules (`backend/engine.py`, `backend/embeddings/embedder.py`, `backend/parsers/pdf_parser.py`) with standard Python `logging` (`logger = logging.getLogger("anyrag.*")`).
  - Added `logging.basicConfig(level=logging.INFO, format="[AnyRAG] %(message)s")` to `backend/cli.py` to preserve clean user-facing terminal output while granting library consumers full control over log filtering and suppression.
  - Authored `pyproject.toml` using `setuptools>=61.0` and PEP 517/621 metadata.
  - Created top-level package wrapper `anyrag/__init__.py` and exposed the unified public API (`AnyRAG`, `VectorStore`, `BM25Index`, `LLMClient`, `LLMError`, `LLMConnectionError`, `LLMGenerationError`, `LlamaServerManager`, `parse_document`, `RecursiveChunker`, `LocalEmbedder`).
  - Registered CLI console script entrypoint `anyrag = "backend.cli:main"`.
- **Automated Test Suite (`tests/test_improvements.py`)**:
  - Created comprehensive test suite verifying typed LLM exceptions, BM25 save/load roundtrips, ChromaDB persistence synchronization, warm server configuration, and top-level package imports.
  - All 9 unit tests passing (`Ran 9 tests in 10.910s, OK`).

---

### [2026-09-20 16:12:00 IST – 16:15:30 IST] — Cloud Primary & Local Offline Fallback Alignment
- **Cloud & Local Fallback Architecture (`backend/config.py` & `backend/agents/llm_client.py`)**:
  - Reconfigured `LLMClient.generate()` to prioritize cloud models with seamless local model runtime as an offline backup.
  - Added `ANYRAG_LOCAL_MODEL_PATH` environment override to allow pointing to any new local GGUF weights.

---

### [2026-09-20 16:16:00 IST – 16:21:30 IST] — OpenRouter Kimi/DeepSeek Primary & Local Phi-4-mini Fallback
- **OpenRouter Cloud Integration (`backend/config.py` & `backend/agents/llm_client.py`)**:
  - Configured high-speed OpenRouter API (`https://openrouter.ai/api/v1`) as primary cloud inference engine.
  - Implemented `_call_openrouter()` with mandatory OpenRouter headers (`Authorization: Bearer <key>`, `HTTP-Referer`, `X-Title`).
  - Added model alias resolution (`OPENROUTER_MODEL_ALIASES`) mapping friendly shorthands (`kimi` -> `moonshotai/kimi-k2`, `deepseek` / `deepseek-chat` -> `deepseek/deepseek-chat`, `deepseek-r1` -> `deepseek/deepseek-r1`).
  - Configured `max_tokens` (default 1024) to avoid OpenRouter reserving the full 100k token context window against user credits.
  - Handled HTTP 402 ("Payment Required" / credit exhaustion) and 429 rate limits as connection errors that gracefully trigger the local offline model cascade.
- **Robust Inference Cascade (`LLMClient.generate(provider="auto")`)**:
  1. **Primary Cloud**: OpenRouter (`moonshotai/kimi-k2` or `deepseek/deepseek-chat`). Verified live with user's `OPENROUTER_API_KEY`.
  2. **Local Fallback**: Standalone warm `llama-server` process with `phi-4-mini` GGUF (~400ms inference).
  3. **Secondary Remote**: Ollama (if service is running/configured).
  4. **Emergency Fallback**: Deterministic grounded extractive synthesis with explicit `⚠️ [Notice: LLM API Unavailable]` notice banner.
- **Automated Verification (`tests/test_improvements.py`)**:
  - Added test cases verifying OpenRouter dispatch, authentication error checks, and simulated network disconnect fallback to local `llama-server`.
  - All 12 unit tests passing in ~2.8s.
- **Security Sandbox Guardrails (`backend/config.py` & `backend/parsers/registry.py`)**:
  - Documented `is_path_allowed()` and `get_allowed_root_directories()` as strict read-only security sandbox boundaries.
  - Guarantees zero file mutation/manipulation during ingestion; prevents traversal or accidental reading of system files (`C:\Windows`, `C:\Program Files`, root credentials).

---

### [2026-09-20 16:45:00 IST – 16:50:00 IST] — Smart PDF Complexity Pre-Scan & Package Cleanup
- **Smart PDF Complexity Detection (`backend/parsers/pdf_parser.py` & `backend/config.py`)**:
  - Implemented sub-5ms heuristic pre-scan `detect_pdf_complexity()` sampling the first pages of incoming PDFs.
  - Detects scanned/image-only pages, dense mathematical/LaTeX notations (`\sum`, `\int`, `\partial`, unmapped unicode font glyphs `\ufffd`), and multi-table lattice structures.
  - In default auto mode (`ANYRAG_USE_DOCLING=auto`), standard narrative reports and documentation use ultra-fast PyMuPDF (~10ms), while complex technical/scientific documents automatically elevate to Docling high-fidelity parser.
  - Graceful fallback: If Docling elevation fails, PDFParser cleanly falls back to PyMuPDF.
- **Packaging Simplification**:
  - Removed top-level `anyrag/` directory and `pyproject.toml` per user preference.
  - Package exports consolidated into `backend/__init__.py`.
  - Added unit tests in `tests/test_improvements.py` (`TestSmartPDFComplexityDetection`). All 14 tests passing in ~2.9s.

---

### [2026-09-20 17:00:00 IST – 17:05:00 IST] — Debate Agent Architecture & Tool Integration Audit

- **`anyrag diff` & `anyrag compare` Re-Classified as Debate Agent Tools**:
  - **`anyrag diff`** (`DocumentComparator.compute_semantic_diff()`): Vectorized chunk-level cosine matrix via `np.matmul` across two documents. Pre-computes three zones used to focus debate:
    - **Overlap Zone** (similarity ≥ 0.70): Topics both documents agree on — skip in debate.
    - **Unique-to-A / Unique-to-B** (similarity ≤ 0.40): Topics only one document covers — key debate territory.
    - **Contradiction Zone** (0.40–0.70): Same topic, different claims — **debate focus hotspot**.
  - **`anyrag compare`** (`DocumentComparator.compare_query()`): Cross-document RAG retrieval with LLM synthesis (dual-persona interrogation). Generates structured comparison with similarities, divergences, unique takeaways, and executive summary.
  - Both tools are designed to serve as intelligence inputs for the upcoming Tri-Party Debate Engine.

- **Same-File Debate Architecture Decision**:
  - Established the rule: when both personas read the **same document**, they share a single `AnyRAG(db_path=...)` instance with separate soul files and conversation histories.
  - When two **different documents** debate, each persona gets its own `AnyRAG` instance with separate Chroma + BM25 indexes to prevent knowledge contamination.

- **Full CLI Command Inventory** (all present in `backend/cli.py`):

  | Command | Purpose |
  |:---|:---|
  | `anyrag ingest <file>` | Parse, chunk, embed, and index a document |
  | `anyrag list` | Show all indexed documents |
  | `anyrag ask <doc> "query"` | Query a grounded document persona |
  | `anyrag search "query"` | Global hybrid search (dense + BM25 RRF) |
  | `anyrag compare doc1 doc2 --query` | Cross-document comparative RAG |
  | `anyrag diff doc1 doc2` | Chunk-level semantic diff (cosine matrix) |
  | `anyrag purge <doc>` | Cascade delete document + embeddings |
  | `anyrag clear` | Wipe entire index |

---

### [2026-09-20 17:07:00 IST – 17:12:00 IST] — Tri-Party Debate Engine & Persona Architecture

- **DocumentPersona Rewrite (`backend/agents/persona.py` — 260 lines)**:
  - **Soul File Loading**: `__init__` accepts `soul_file: Path` — reads a `.md` file defining persona's worldview, stance, grounding rules, and personality. Falls back to default Jarvis prompt if no soul file is provided.
  - **Persistent Conversation Log (`convo.jsonl`)**: Every `.ask()` call appends a full turn record (turn number, UTC timestamp, speaker, persona name, query, answer, citation list with section titles, scores, and page numbers) to an append-only JSONL file.
  - **Rolling Summary (`summary_{persona}.md`)**: Every `summary_interval` turns (default 4), the LLM generates a compressed summary of recent turns (max 150 words) capturing key facts, agreements, and open questions. Written in the persona's voice. Persisted to disk and injected into the system prompt as `[Conversation Memory]`.
  - **Anchor Question Injection**: `set_anchor_question()` stores the original debate question. It is re-injected into every system prompt as `[Anchor Topic]` to prevent multi-turn topic drift.
  - **Session Resumption**: On initialization, existing `convo.jsonl` and `summary_{persona}.md` are loaded from disk, allowing a persona to resume mid-conversation across process restarts.

- **Tri-Party Debate Engine (`backend/agents/debate.py` — 310 lines) [NEW]**:
  - **`DebateSession` Class**: Orchestrates two `DocumentPersona` instances debating each other with the user as the third participant.
  - **Same-Document Mode**: Both personas share a single `VectorStore`. Differentiation comes from soul files, conversation histories, and rolling summaries.
  - **Cross-Document Mode**: Each persona gets its own `VectorStore` to prevent knowledge contamination. Pre-debate `compute_semantic_diff()` runs automatically to map overlap/unique/contradiction zones.
  - **`start_debate(question)`**: Launches the debate with an anchor question. Both personas give opening statements. Persona B sees Persona A's opening to enable reactive argumentation.
  - **`next_round(user_input=None)`**: Executes subsequent rounds. Optional `user_input` lets the user steer or challenge. Without it, personas continue debating autonomously.
  - **Speakable Response Enforcement**: All debate prompts enforce "2-4 sentences, max 90 words, conversational tone" — designed for overlay HUD display, not essay generation.
  - **Persistent Dual-File Storage**:
    - `convo.jsonl`: Lossless debate transcript with round numbers, timestamps, both persona statements, and user inputs.
    - `summary_{persona}.md`: Per-persona rolling memory.
  - **Session Structure**: Each debate creates a directory under `data/debates/debate_{timestamp}/` containing `convo.jsonl`, `persona_a/`, and `persona_b/` subdirectories.

- **Usage Examples**:
  ```python
  # Same-document debate
  engine = AnyRAG(db_path="./data/shared_index")
  session = DebateSession(
      doc1_id="doc_abc", vector_store_1=engine.vector_store,
      soul_file_a="souls/optimist.md", soul_file_b="souls/critic.md"
  )
  opening = session.start_debate("Is this paper's methodology sound?")
  round2 = session.next_round("What about the sample size?")

  # Cross-document debate
  engine_a = AnyRAG(db_path="./data/doc_a_index")
  engine_b = AnyRAG(db_path="./data/doc_b_index")
  session = DebateSession(
      doc1_id="paper_a", vector_store_1=engine_a.vector_store,
      doc2_id="paper_b", vector_store_2=engine_b.vector_store
  )
  session.run_pre_debate_diff()  # Maps contradiction zones
  opening = session.start_debate("Which approach is more effective?")
  ```

---

### [2026-09-20 17:22:00 IST – 17:26:00 IST] — Soul Consolidation & DB Cleanup

- **Soul Architecture Unified (`docs/souls/`)**:
  - Replaced scattered persona files with a single comprehensive, all-in-one soul template: [`docs/souls/default.md`](file:///c:/Users/iqand/Downloads/ANYRAG/docs/souls/default.md).
  - Created [`docs/souls/SOUL_CREATOR.md`](file:///c:/Users/iqand/Downloads/ANYRAG/docs/souls/SOUL_CREATOR.md): Blueprint specification detailing every reasoning knob, natural human verbal transitions, debate strategy options, anti-patterns, and instructions for authoring custom souls.
  - Removed obsolete individual souls (`analyst.md`, `devils_advocate.md`, `synthesizer.md`, `pragmatist.md`).
- **Database & Storage Residue Purge**:
  - Purged ChromaDB vector collections and metadata residues via `rag.clear()` to maintain a clean testing slate for production sessions.
  - Retained essential offline assets: GGUF model weights ([`phi-4-mini`](file:///c:/Users/iqand/Downloads/ANYRAG/assets/models/phi-4-mini-[3.8b-q4_k_m]-abliterated.gguf)) and local ONNX embedding weights ([`all-MiniLM-L6-v2`](file:///c:/Users/iqand/Downloads/ANYRAG/assets/embeddings/all-MiniLM-L6-v2)).

---

### [2026-09-20 17:26:00 IST – 17:28:00 IST] — Philosophy Alignment with Speakable Tri-Party Debate Vision

- **Rewrote `docs/PHILOSOPHY.md` & `README.md`**:
  - Updated foundational principles to match the conversational persona debate vision:
    1. **Speakable Human Dialogue ("Roundtable, Not an Essay")**: Natural spoken cadence, 2–4 sentences (under 90 words), authentic concessions ("I'll give you that, but..."), and no markdown formatting in spoken dialogue turns.
    2. **Tri-Party Debate Architecture**: Clear separation of same-document debate (shared index, divergent soul/memory) vs. cross-document debate (isolated vector stores preventing knowledge bleed).
    3. **Debate Intelligence Tools (`diff` & `compare`)**: Matrix cosine similarity (`np.matmul`) maps consensus overlaps vs. contradiction hotspots prior to debate rounds, with live cross-retrieval for targeted challenges.
    4. **Dual-Tier Memory & Topic Grounding**: Persistent append-only lossless logging (`convo.jsonl`) paired with rolling 150-word compressed memories (`summary_{persona}.md`) and persistent anchor question re-injection.
    5. **High-Speed Cloud with Local Sovereignty**: Primary cloud inference via OpenRouter (Kimi / DeepSeek) for fast, natural dialogue flow with seamless local fallback to warm `llama-server` (`phi-4-mini`) and 100% local embedding/vector storage.

---

### [2026-09-20 17:36:00 IST – 17:41:00 IST] — Critical Debate Engine Bugfixes

1. **Cross-Document Semantic Diff Dual-Store Support (`backend/agents/comparator.py` & `backend/agents/debate.py`)**:
   - Upgraded `DocumentComparator` to take `vector_store_1` and an optional isolated `vector_store_2`.
   - In cross-document debates, `compute_semantic_diff()` now correctly pulls chunks for Document 1 from `vector_store_1` and Document 2 from `vector_store_2`.
   - Completely resolved the bug where Document 2's chunks were searched inside Document 1's store, preventing silent failure of contradiction-zone pre-computation.

2. **Clean Retrieval Query Decoupling (`backend/agents/persona.py` & `backend/agents/debate.py`)**:
   - Decoupled search retrieval from prompt generation: `DocumentPersona.ask(query, retrieval_query=...)`.
   - In multi-turn debate rounds, BM25 and dense vector search now execute strictly against the clean anchor question and substantive opponent claims.
   - Completely eliminated prompt scaffolding pollution (e.g. meta-instructions like *"DEBATE TOPIC"*, *"conversational"*, *"under 90 words"*, and speaker tags) from polluting IDF calculations and semantic embeddings.

3. **Hybrid Memory: Immediate Stance Retention Between Summaries (`backend/agents/persona.py`)**:
   - Enhanced `DocumentPersona.get_system_prompt()` to inject recent unsummarized dialogue turns (`history[-2:]`) directly alongside the rolling summary.
   - Eliminates the stance amnesia blind spot between summary intervals (default 4 turns), guaranteeing each persona maintains full conversational continuity and never contradicts its own recent arguments.

4. **Automated Regression Suite (`tests/test_debate_fixes.py`)**:
   - Added unit tests asserting dual-store diff calculation, clean search query decoupling, and recent turn injection in the persona system prompt.
   - **Verification**: Executed `python -m unittest tests/test_debate_fixes.py` — all 3 unit tests passed in 4.38s with zero regressions.

---

### [2026-09-20 17:53:00 IST – 17:57:00 IST] — Autonomous Objection & Speculative Background Interjection

- **Autonomous Watchdog Architecture (`DebateSession.evaluate_objection`)**:
  - Implemented listening logic: whenever a persona or user finishes speaking, the inactive persona evaluates the spoken claim against its own document.
  - **Factual Contradiction**: If the claim contradicts, distorts, or misrepresents evidence in its document, the listener generates a sharp, speakable objection (2–3 sentences, max 75 words).
  - **Silent Pass**: If the claim is accurate, uncontested, or unsupported by counter-evidence, the model returns strictly `[PASS]`, producing zero screen or audio clutter.
- **Concurrent Speculative Background Execution (`DebateSession.address_persona`)**:
  - While the primary speaker is talking or streaming, the inactive persona initiates retrieval and speculation in a background thread via `concurrent.futures.ThreadPoolExecutor`.
  - When the primary speaker finishes, the objection response is already waiting in memory, delivering instantaneous, zero-latency interjections.
- **Regression Verification (`tests/test_debate_fixes.py`)**:
  - Added unit test `test_autonomous_objection_pass_when_accurate`: Confirmed `[PASS]` output cleanly yields `None`.
  - Added unit test `test_autonomous_objection_triggers_on_contradiction`: Confirmed contradictory statements trigger immediate grounded objection payloads.

---

### [2026-09-20 18:00:00 IST – 18:03:00 IST] — Mutual Watchdog & Single-Speaker Deduplication

- **Symmetric Mutual Checking (`DebateSession.check_user_statement`)**:
  - Both Document A and Document B act as watchdogs for each other and for the user.
  - If the user makes a statement or query containing a factual inaccuracy, both personas evaluate it in parallel against their respective grounded documents.
- **Single-Speaker Deduplication Rule (`DebateSession._deduplicate_objections`)**:
  - **The Problem**: If both Doc A and Doc B detect that the user or another speaker made an error, having both shout objections at the same time is chaotic and unnatural.
  - **The Solution**: Exactly one persona speaks to correct the mistake. If both personas flag the identical contradiction, Persona A voices the objection while Persona B discards its speech (co-signing the flag silently), preventing double-speaking.
- **Automated Verification (`tests/test_debate_fixes.py`)**:
  - Added unit test `test_check_user_statement_deduplication`: Verified that when both documents contradict a user's statement, exactly one persona delivers the objection while the second yields and discards redundant speech.


