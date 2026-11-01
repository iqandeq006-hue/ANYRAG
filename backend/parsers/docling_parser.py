import importlib.util
from pathlib import Path
from typing import List, Optional, Any, Union
from .base import BaseParser, ExtractedDocument, ExtractedSection


def is_docling_available() -> bool:
    """Fast check for Docling availability without eagerly importing PyTorch/ML dependencies."""
    return importlib.util.find_spec("docling") is not None


# Backwards-compatible alias (computed without heavy ML imports)
HAS_DOCLING = is_docling_available()


class DoclingPDFParser(BaseParser):
    """
    Advanced PDF parser adapter powered by Docling (IBM).
    Designed specifically for documents containing complex multi-column layouts
    and tables with merged cells, nested headers, or multi-line entries.
    """

    def __init__(self):
        self._converter = None

    def _get_converter(self):
        if not is_docling_available():
            raise ImportError(
                "Docling is required for DoclingPDFParser. Install it with: pip install docling"
            )
        if self._converter is None:
            # Lazy import: Docling has significant import time and pulls in heavy ML/torch dependencies.
            # Defer until converter is actually initialized.
            from docling.document_converter import DocumentConverter
            self._converter = DocumentConverter()
        return self._converter

    def parse(self, file_path: Union[str, Path]) -> ExtractedDocument:
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        doc_id = ExtractedDocument.generate_id(file_path)
        converter = self._get_converter()

        # Convert document
        result = converter.convert(str(file_path))
        doc = result.document

        sections: List[ExtractedSection] = []

        # 1. Extract complex tables with merged cells to Markdown
        if hasattr(doc, "tables") and doc.tables:
            for idx, table in enumerate(doc.tables, 1):
                try:
                    # Docling table provides export_to_markdown() or export_to_dataframe()
                    if hasattr(table, "export_to_markdown"):
                        try:
                            table_md = table.export_to_markdown(doc=doc)
                        except TypeError:
                            table_md = table.export_to_markdown()
                    elif hasattr(table, "export_to_dataframe"):
                        df = table.export_to_dataframe()
                        table_md = df.to_markdown(index=False)
                    else:
                        table_md = str(table)

                    if not table_md or not table_md.strip():
                        continue

                    # Extract page number provenance if available
                    page_no = None
                    if hasattr(table, "prov") and table.prov:
                        page_no = getattr(table.prov[0], "page_no", None)

                    sections.append(ExtractedSection(
                        content=table_md.strip(),
                        section_title=f"Complex Table {idx}",
                        page_number=page_no,
                        section_type="table",
                        metadata={
                            "table_index": idx,
                            "page": page_no,
                            "extractor": "docling",
                        }
                    ))
                except Exception:
                    continue

        table_count = sum(1 for s in sections if s.section_type == "table")

        # 2. Extract structured full text / markdown
        try:
            full_markdown = doc.export_to_markdown()
        except Exception:
            full_markdown = ""

        if full_markdown and full_markdown.strip():
            # If doc has markdown export, chunk into logical header-based or block sections
            sections.append(ExtractedSection(
                content=full_markdown.strip(),
                section_title=f"{file_path.stem} (Docling Content)",
                section_type="markdown",
                metadata={"extractor": "docling"}
            ))

        # Fallback raw_text if full_markdown was empty
        raw_text = full_markdown.strip() if full_markdown and full_markdown.strip() else "\n\n".join(s.content for s in sections)

        return ExtractedDocument(
            doc_id=doc_id,
            file_path=str(file_path),
            file_name=file_path.name,
            file_type="pdf",
            file_size=file_path.stat().st_size,
            sections=sections,
            raw_text=raw_text,
            metadata={
                "parser": "docling",
                "has_complex_tables": table_count > 0,
                "tables_count": table_count,
            }
        )
