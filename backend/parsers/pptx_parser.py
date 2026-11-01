from pathlib import Path
from typing import List
import pptx
from .base import BaseParser, ExtractedDocument, ExtractedSection

class PPTXParser(BaseParser):
    def parse(self, file_path: Path) -> ExtractedDocument:
        doc_id = ExtractedDocument.generate_id(file_path)
        prs = pptx.Presentation(str(file_path))
        sections: List[ExtractedSection] = []
        full_text_parts: List[str] = []

        total_slides = len(prs.slides)
        for slide_idx, slide in enumerate(prs.slides):
            slide_num = slide_idx + 1
            slide_title = f"Slide {slide_num}"
            slide_texts: List[str] = []

            # Check for title
            if slide.shapes.title and slide.shapes.title.text.strip():
                slide_title = slide.shapes.title.text.strip()

            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text and text != slide_title:
                            slide_texts.append(text)
                elif shape.has_table:
                    # Extract table from slide
                    table = shape.table
                    table_rows = []
                    for row in table.rows:
                        row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                        table_rows.append(row_cells)
                    if table_rows:
                        table_lines = []
                        header = table_rows[0]
                        table_lines.append("| " + " | ".join(header) + " |")
                        table_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                        for row in table_rows[1:]:
                            table_lines.append("| " + " | ".join(row) + " |")
                        slide_texts.append("\n".join(table_lines))

            # Check notes slide
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    slide_texts.append(f"[Speaker Notes]: {notes}")

            combined_content = "\n".join(slide_texts)
            sections.append(ExtractedSection(
                content=f"# {slide_title}\n{combined_content}" if combined_content else f"# {slide_title}",
                section_title=slide_title,
                page_number=slide_num,
                section_type="slide",
                metadata={"slide_number": slide_num}
            ))

            full_text_parts.append(f"## Slide {slide_num}: {slide_title}\n{combined_content}")

        raw_text = "\n\n".join(full_text_parts)
        return ExtractedDocument(
            doc_id=doc_id,
            file_path=str(file_path.resolve()),
            file_name=file_path.name,
            file_type="pptx",
            file_size=file_path.stat().st_size,
            sections=sections,
            raw_text=raw_text,
            metadata={"total_slides": total_slides}
        )
