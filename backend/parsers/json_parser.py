import json
from pathlib import Path
from typing import List, Any
from .base import BaseParser, ExtractedDocument, ExtractedSection

class JSONParser(BaseParser):
    """
    Dedicated JSON parser that extracts structured key-value sections and record batches
    instead of treating the entire document as a flat, unorganized text blob.
    """
    def __init__(self, array_batch_size: int = 5, max_chars_per_section: int = 2000):
        self.array_batch_size = array_batch_size
        self.max_chars_per_section = max_chars_per_section

    def _format_value(self, val: Any) -> str:
        """Format a value into human/LLM friendly structured text."""
        if isinstance(val, (dict, list)):
            return json.dumps(val, indent=2, ensure_ascii=False)
        return str(val)

    def parse(self, file_path: Path) -> ExtractedDocument:
        doc_id = ExtractedDocument.generate_id(file_path)

        raw_bytes = file_path.read_bytes()
        text = ""
        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                text = raw_bytes.decode(encoding)
                break
            except (UnicodeDecodeError, Exception):
                continue

        if not text:
            text = raw_bytes.decode("utf-8", errors="replace")

        try:
            data = json.loads(text)
        except Exception:
            # If invalid JSON, fallback to single section
            sections = [ExtractedSection(
                content=text.strip(),
                section_title=file_path.stem,
                section_type="json_raw"
            )]
            return ExtractedDocument(
                doc_id=doc_id,
                file_path=str(file_path.resolve()),
                file_name=file_path.name,
                file_type="json",
                file_size=file_path.stat().st_size,
                sections=sections,
                raw_text=text,
                metadata={"valid_json": False}
            )

        sections: List[ExtractedSection] = []

        if isinstance(data, dict):
            # Parse by top-level keys
            for key, val in data.items():
                title = f"{file_path.stem}.{key}"
                formatted = self._format_value(val)

                # If the key contains a list of records and it's large, split into batches
                if isinstance(val, list) and len(val) > self.array_batch_size and len(formatted) > self.max_chars_per_section:
                    for i in range(0, len(val), self.array_batch_size):
                        batch = val[i : i + self.array_batch_size]
                        batch_title = f"{file_path.stem}.{key}[{i}:{i + len(batch)}]"
                        batch_content = f"### Field: {key} (Items {i} to {i + len(batch) - 1})\n" + json.dumps(batch, indent=2, ensure_ascii=False)
                        sections.append(ExtractedSection(
                            content=batch_content,
                            section_title=batch_title,
                            section_type="json_array_batch",
                            metadata={"key": key, "start_index": i, "batch_size": len(batch)}
                        ))
                else:
                    content = f"### Field: {key}\n{formatted}"
                    sections.append(ExtractedSection(
                        content=content,
                        section_title=title,
                        section_type="json_object",
                        metadata={"key": key, "value_type": type(val).__name__}
                    ))

        elif isinstance(data, list):
            # Array of items at top level
            total_items = len(data)
            if total_items == 0:
                sections.append(ExtractedSection(
                    content="[]",
                    section_title=f"{file_path.stem} (Empty Array)",
                    section_type="json_array"
                ))
            else:
                for i in range(0, total_items, self.array_batch_size):
                    batch = data[i : i + self.array_batch_size]
                    title = f"{file_path.stem}[{i}:{i + len(batch)}]"
                    content = f"### Items {i} to {i + len(batch) - 1} of {total_items}\n" + json.dumps(batch, indent=2, ensure_ascii=False)
                    sections.append(ExtractedSection(
                        content=content,
                        section_title=title,
                        section_type="json_array_batch",
                        metadata={"start_index": i, "batch_size": len(batch), "total_items": total_items}
                    ))
        else:
            # Primitive top-level value
            sections.append(ExtractedSection(
                content=str(data),
                section_title=file_path.stem,
                section_type="json_primitive"
            ))

        return ExtractedDocument(
            doc_id=doc_id,
            file_path=str(file_path.resolve()),
            file_name=file_path.name,
            file_type="json",
            file_size=file_path.stat().st_size,
            sections=sections,
            raw_text=text,
            metadata={
                "extension": ".json",
                "is_dict": isinstance(data, dict),
                "is_list": isinstance(data, list),
                "top_level_keys": list(data.keys()) if isinstance(data, dict) else [],
                "section_count": len(sections)
            }
        )
