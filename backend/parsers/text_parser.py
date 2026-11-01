import re
from pathlib import Path
from typing import List
from .base import BaseParser, ExtractedDocument, ExtractedSection

class TextParser(BaseParser):
    def parse(self, file_path: Path) -> ExtractedDocument:
        doc_id = ExtractedDocument.generate_id(file_path)
        ext = file_path.suffix.lower()

        # Read file with encoding fallbacks
        text = ""
        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    text = f.read()
                break
            except (UnicodeDecodeError, Exception):
                continue

        sections: List[ExtractedSection] = []

        if ext in [".md", ".markdown"]:
            # Split markdown by top-level headers (# or ##)
            header_pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
            splits = header_pattern.split(text)

            if len(splits) > 1:
                # Leading content before first header
                if splits[0].strip():
                    sections.append(ExtractedSection(
                        content=splits[0].strip(),
                        section_title="Introduction",
                        section_type="text"
                    ))
                # Iterate over header and body pairs
                for i in range(1, len(splits), 2):
                    header = splits[i].strip()
                    content = splits[i+1].strip() if i+1 < len(splits) else ""
                    sections.append(ExtractedSection(
                        content=f"{header}\n\n{content}".strip(),
                        section_title=header.lstrip("#").strip(),
                        section_type="markdown_section"
                    ))
            else:
                sections.append(ExtractedSection(content=text.strip(), section_title=file_path.stem))
        else:
            # Plain text, CSV, JSON, code
            sections.append(ExtractedSection(
                content=text.strip(),
                section_title=file_path.stem,
                section_type=ext.lstrip(".") or "text"
            ))

        return ExtractedDocument(
            doc_id=doc_id,
            file_path=str(file_path.resolve()),
            file_name=file_path.name,
            file_type=ext.lstrip(".") or "text",
            file_size=file_path.stat().st_size,
            sections=sections,
            raw_text=text,
            metadata={"extension": ext}
        )
