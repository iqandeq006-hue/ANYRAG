from pathlib import Path
from typing import List
import docx
from .base import BaseParser, ExtractedDocument, ExtractedSection

class DocxParser(BaseParser):
    def parse(self, file_path: Path) -> ExtractedDocument:
        doc_id = ExtractedDocument.generate_id(file_path)
        doc = docx.Document(str(file_path))
        sections: List[ExtractedSection] = []
        full_text_parts: List[str] = []

        current_heading = "Introduction"
        current_paragraphs: List[str] = []

        # 1. Process paragraphs & headings
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            style_name = para.style.name.lower() if para.style else ""
            if "heading" in style_name or "title" in style_name:
                if current_paragraphs:
                    content = "\n\n".join(current_paragraphs)
                    sections.append(ExtractedSection(
                        content=content,
                        section_title=current_heading,
                        section_type="text",
                        metadata={"heading": current_heading}
                    ))
                    full_text_parts.append(f"### {current_heading}\n{content}")
                    current_paragraphs = []
                current_heading = text
            else:
                current_paragraphs.append(text)

        if current_paragraphs:
            content = "\n\n".join(current_paragraphs)
            sections.append(ExtractedSection(
                content=content,
                section_title=current_heading,
                section_type="text",
                metadata={"heading": current_heading}
            ))
            full_text_parts.append(f"### {current_heading}\n{content}")

        # 2. Process tables
        for t_idx, table in enumerate(doc.tables):
            rows_data = []
            for row in table.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                rows_data.append(row_cells)

            if rows_data:
                table_lines = []
                header = rows_data[0]
                table_lines.append("| " + " | ".join(header) + " |")
                table_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                for row in rows_data[1:]:
                    table_lines.append("| " + " | ".join(row) + " |")
                table_md = "\n".join(table_lines)
                sections.append(ExtractedSection(
                    content=table_md,
                    section_title=f"Table {t_idx + 1}",
                    section_type="table",
                    metadata={"table_index": t_idx + 1}
                ))
                full_text_parts.append(table_md)

        raw_text = "\n\n".join(full_text_parts)
        return ExtractedDocument(
            doc_id=doc_id,
            file_path=str(file_path.resolve()),
            file_name=file_path.name,
            file_type="docx",
            file_size=file_path.stat().st_size,
            sections=sections,
            raw_text=raw_text,
            metadata={"paragraph_count": len(doc.paragraphs), "table_count": len(doc.tables)}
        )
