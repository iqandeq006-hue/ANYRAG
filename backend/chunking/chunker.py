from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import hashlib
from backend.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from backend.parsers.base import ExtractedDocument, ExtractedSection

@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    doc_name: str
    doc_path: str
    content: str
    chunk_index: int
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    section_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)

class RecursiveChunker:
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    def _split_text(self, text: str) -> List[str]:
        """Split a long text string into overlapping chunks."""
        text = text.strip()
        if len(text) <= self.chunk_size:
            return [text] if text else []

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break

            # Find best split point using separators
            split_pos = -1
            sub = text[start:end]
            for sep in self.separators:
                idx = sub.rfind(sep)
                if idx != -1 and idx > int(self.chunk_size * 0.3):
                    split_pos = start + idx + len(sep)
                    break

            if split_pos == -1:
                split_pos = end

            chunk = text[start:split_pos].strip()
            if chunk:
                chunks.append(chunk)

            # Move forward with overlap
            next_start = split_pos - self.chunk_overlap
            if next_start <= start:
                next_start = start + max(1, int(self.chunk_size * 0.5))
            start = next_start

        return chunks

    def chunk_document(self, doc: ExtractedDocument) -> List[DocumentChunk]:
        """Convert an ExtractedDocument into an ordered list of DocumentChunks."""
        chunks: List[DocumentChunk] = []
        global_index = 0

        for sec in doc.sections:
            sec_content = sec.content.strip()
            if not sec_content:
                continue

            # If section is a table and not monstrously large, keep table intact
            if sec.section_type == "table" and len(sec_content) <= self.chunk_size * 2:
                sub_chunks = [sec_content]
            else:
                sub_chunks = self._split_text(sec_content)

            for sub in sub_chunks:
                # Add contextual header if available
                context_prefix = ""
                if sec.section_title and not sub.startswith("#"):
                    context_prefix = f"[{sec.section_title}] "

                final_content = context_prefix + sub
                chunk_hash = hashlib.sha256(f"{doc.doc_id}_{global_index}_{final_content}".encode("utf-8")).hexdigest()[:16]

                chunks.append(DocumentChunk(
                    chunk_id=chunk_hash,
                    doc_id=doc.doc_id,
                    doc_name=doc.file_name,
                    doc_path=doc.file_path,
                    content=final_content,
                    chunk_index=global_index,
                    section_title=sec.section_title,
                    page_number=sec.page_number,
                    section_type=sec.section_type,
                    metadata=dict(sec.metadata, file_type=doc.file_type)
                ))
                global_index += 1

        return chunks
