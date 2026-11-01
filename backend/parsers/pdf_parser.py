import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple
import fitz  # PyMuPDF
from backend.config import USE_DOCLING_FOR_PDF
from .base import BaseParser, ExtractedDocument, ExtractedSection
from .docling_parser import is_docling_available

logger = logging.getLogger("anyrag.pdf_parser")


def detect_pdf_complexity(doc: fitz.Document) -> Tuple[bool, str]:
    """
    Sub-5ms heuristic pre-scan of the first sample pages to detect if the PDF
    contains complex layouts requiring the Docling high-fidelity parser:
    1. Scanned / image-only pages lacking embedded digital text.
    2. Dense mathematical formulas, LaTeX operators, or scientific symbols.
    3. Heavy / complex multi-table structures or dense vector gridlines.
    """
    sample_pages = min(len(doc), 5)
    total_text_len = 0
    total_images = 0
    total_tables = 0
    math_symbol_count = 0

    # Common math symbols, unmapped font glyphs, and LaTeX operators: ∑, ∫, ∂, √, ∏, ±, ≤, ≥, ≠, ≈, ∞, etc.
    math_regex = re.compile(
        r"[\u2200-\u22FF\u2A00-\u2AFF\u0370-\u03FF\uFFFD\u2208\u211D∫∑∂√∏±≤≥≠≈∞÷×]|(?:\\b(?:sum|int|frac|partial|alpha|beta|sigma|lambda|theta|infty|approx|times|div|sqrt|matrix|equation)\\b)"
    )

    for idx in range(sample_pages):
        page = doc[idx]
        text = page.get_text()
        total_text_len += len(text.strip())

        # Check image density
        try:
            images = page.get_images()
            total_images += len(images)
        except Exception:
            pass

        # Check math symbols
        math_matches = math_regex.findall(text)
        math_symbol_count += len(math_matches)

        # Check table density
        try:
            tables = page.find_tables(strategy="lines")
            total_tables += len(tables)
        except Exception:
            pass

    # Heuristic 1: Scanned document (image present with little or no digital text)
    if total_images >= 1 and (total_text_len / max(sample_pages, 1)) < 60:
        return True, f"Scanned/image-only document detected (avg text {total_text_len // max(sample_pages, 1)} chars, {total_images} images)"

    # Heuristic 2: Dense mathematical / scientific notation
    if math_symbol_count >= 8:
        return True, f"Dense mathematical/scientific notation detected ({math_symbol_count} math symbols across {sample_pages} pages)"

    # Heuristic 3: Multiple complex tabular structures
    if total_tables >= 3:
        return True, f"Multiple complex tabular structures detected ({total_tables} tables across {sample_pages} pages)"

    return False, "Standard narrative or structured document"


class PDFParser(BaseParser):
    def __init__(self, use_docling: Optional[bool] = None):
        # None = Auto-detect based on heuristic pre-scan
        # True = Always force Docling
        # False = Always use PyMuPDF
        self.use_docling = USE_DOCLING_FOR_PDF if use_docling is None else use_docling

    def parse(self, file_path: Path) -> ExtractedDocument:
        file_path = Path(file_path).resolve()
        doc = fitz.open(str(file_path))

        should_use_docling = False
        reason = ""

        if self.use_docling is True:
            should_use_docling = True
            reason = "Forced via configuration (ANYRAG_USE_DOCLING=true)"
        elif self.use_docling is None and is_docling_available():
            is_complex, reason = detect_pdf_complexity(doc)
            if is_complex:
                should_use_docling = True

        if should_use_docling:
            try:
                from .docling_parser import DoclingPDFParser
                logger.info(f"Auto-elevating {file_path.name} to Docling parser: {reason}")
                doc.close()
                return DoclingPDFParser().parse(file_path)
            except Exception as e:
                logger.warning(f"Docling elevation failed ({e}). Falling back to fast PyMuPDF parser.")
                doc = fitz.open(str(file_path))

        doc_id = ExtractedDocument.generate_id(file_path)
        sections: List[ExtractedSection] = []
        full_text_parts: List[str] = []

        total_pages = len(doc)
        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]

            # 1. Dual-Strategy Table Extraction (Pass 1: Lattice lines, Pass 2: Stream whitespace)
            tables_text = []
            extracted_rects = []

            def _is_valid_table(data_matrix) -> bool:
                if not data_matrix or len(data_matrix) < 2:
                    return False
                row_lens = [len(r) for r in data_matrix if r]
                if not row_lens or max(row_lens) < 2:
                    return False
                # Cell density check: ratio of non-empty cells
                total_cells = sum(len(r) for r in data_matrix)
                non_empty = sum(1 for r in data_matrix for c in r if str(c or "").strip())
                if total_cells == 0 or (non_empty / total_cells) < 0.35:
                    return False
                return True

            def _format_markdown_table(data_matrix) -> str:
                max_cols = max(len(r) for r in data_matrix)
                header = data_matrix[0] + [""] * (max_cols - len(data_matrix[0]))
                table_lines = [
                    "| " + " | ".join(str(c or "").strip() for c in header) + " |",
                    "| " + " | ".join(["---"] * max_cols) + " |"
                ]
                for row in data_matrix[1:]:
                    padded_row = row + [""] * (max_cols - len(row))
                    table_lines.append("| " + " | ".join(str(c or "").strip() for c in padded_row) + " |")
                return "\n".join(table_lines)

            # Pass 1: Lattice strategy (explicit lines and borders)
            try:
                lattice_tables = page.find_tables(strategy="lines")
                for table in lattice_tables:
                    df = table.extract()
                    if _is_valid_table(df):
                        formatted_table = _format_markdown_table(df)
                        tables_text.append(formatted_table)
                        extracted_rects.append(fitz.Rect(table.bbox))
                        sections.append(ExtractedSection(
                            content=formatted_table,
                            section_title=f"Page {page_num} Table (Lattice)",
                            page_number=page_num,
                            section_type="table",
                            metadata={"page": page_num, "strategy": "lattice", "rows": len(df)}
                        ))
            except Exception:
                pass

            # Pass 2: Stream strategy (borderless whitespace-aligned tabular data)
            try:
                stream_tables = page.find_tables(strategy="text")
                for table in stream_tables:
                    t_rect = fitz.Rect(table.bbox)
                    # Exclude stream tables overlapping with already extracted lattice tables
                    if any(t_rect.intersects(r) for r in extracted_rects):
                        continue

                    df = table.extract()
                    if _is_valid_table(df):
                        formatted_table = _format_markdown_table(df)
                        tables_text.append(formatted_table)
                        extracted_rects.append(t_rect)
                        sections.append(ExtractedSection(
                            content=formatted_table,
                            section_title=f"Page {page_num} Table (Stream)",
                            page_number=page_num,
                            section_type="table",
                            metadata={"page": page_num, "strategy": "stream", "rows": len(df)}
                        ))
            except Exception:
                pass

            # 2. Extract standard text blocks
            blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
            page_text_blocks = []
            for b in blocks:
                if len(b) >= 5 and b[4]:
                    text = b[4].strip()
                    if text:
                        page_text_blocks.append(text)

            combined_page_text = "\n\n".join(page_text_blocks)
            if combined_page_text:
                sections.append(ExtractedSection(
                    content=combined_page_text,
                    section_title=f"Page {page_num}",
                    page_number=page_num,
                    section_type="text",
                    metadata={"page": page_num}
                ))
                full_text_parts.append(f"--- Page {page_num} ---\n{combined_page_text}")

            if tables_text:
                full_text_parts.extend(tables_text)

        doc.close()

        raw_text = "\n\n".join(full_text_parts)
        return ExtractedDocument(
            doc_id=doc_id,
            file_path=str(file_path.resolve()),
            file_name=file_path.name,
            file_type="pdf",
            file_size=file_path.stat().st_size,
            sections=sections,
            raw_text=raw_text,
            metadata={"total_pages": total_pages}
        )
