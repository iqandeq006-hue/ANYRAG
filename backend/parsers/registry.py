from pathlib import Path
from typing import Dict, Type
from backend.config import is_path_allowed, ALLOWED_EXTENSIONS
from .base import BaseParser, ExtractedDocument
from .pdf_parser import PDFParser
from .docx_parser import DocxParser
from .pptx_parser import PPTXParser
from .text_parser import TextParser
from .csv_parser import CSVParser
from .json_parser import JSONParser
from .code_parser import CodeParser
from .html_parser import HTMLParser

class ParserRegistry:
    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {
            ".pdf": PDFParser(),
            ".docx": DocxParser(),
            ".pptx": PPTXParser(),
            ".md": TextParser(),
            ".markdown": TextParser(),
            ".txt": TextParser(),
            ".csv": CSVParser(),
            ".json": JSONParser(),
            ".py": CodeParser(),
            ".html": HTMLParser(),
            ".htm": HTMLParser(),
        }
        self._default_text_parser = TextParser()

    def parse(self, file_path: str | Path) -> ExtractedDocument:
        path = Path(file_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not is_path_allowed(path):
            raise PermissionError(
                f"Access denied: Ingestion is restricted to Documents, Downloads, Pictures, Videos (and subfolders). Path not allowed: {path}"
            )

        ext = path.suffix.lower()
        parser = self._parsers.get(ext, self._default_text_parser)
        return parser.parse(path)

# Global default instance
default_registry = ParserRegistry()

def parse_document(file_path: str | Path) -> ExtractedDocument:
    return default_registry.parse(file_path)
