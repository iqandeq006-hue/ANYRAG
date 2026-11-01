from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import time

@dataclass
class ExtractedSection:
    content: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    section_type: str = "text"  # text, table, slide, header, code
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExtractedDocument:
    doc_id: str
    file_path: str
    file_name: str
    file_type: str
    file_size: int
    sections: List[ExtractedSection] = field(default_factory=list)
    raw_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def generate_id(file_path: Path) -> str:
        """Generate deterministic doc_id from file path and content or mtime."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read up to 2MB to compute hash quickly
                chunk = f.read(2 * 1024 * 1024)
                hasher.update(chunk)
        except Exception:
            hasher.update(str(file_path).encode("utf-8"))
            hasher.update(str(file_path.stat().st_mtime if file_path.exists() else time.time()).encode("utf-8"))
        return hasher.hexdigest()[:16]

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> ExtractedDocument:
        """Parse document file into structured ExtractedDocument."""
        pass
