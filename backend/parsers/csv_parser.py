import csv
import io
from pathlib import Path
from typing import List, Optional
from .base import BaseParser, ExtractedDocument, ExtractedSection

class CSVParser(BaseParser):
    """
    Dedicated CSV parser that preserves tabular structure and column headers.
    Splits rows into manageable table chunks while carrying column headers with every chunk,
    ensuring downstream semantic embeddings preserve full column context.
    """
    def __init__(self, batch_size: int = 15):
        self.batch_size = batch_size

    def parse(self, file_path: Path) -> ExtractedDocument:
        doc_id = ExtractedDocument.generate_id(file_path)

        # Read content with encoding fallbacks
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

        # Detect dialect / delimiter
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample)
        except Exception:
            dialect = csv.excel

        reader = csv.reader(io.StringIO(text), dialect=dialect)
        rows: List[List[str]] = []
        for r in reader:
            if any(cell.strip() for cell in r):
                rows.append([cell.strip() for cell in r])

        sections: List[ExtractedSection] = []
        headers: List[str] = []

        if rows:
            headers = rows[0]
            data_rows = rows[1:]
            total_data_rows = len(data_rows)

            if total_data_rows == 0:
                # Only header row
                header_line = "| " + " | ".join(headers) + " |"
                separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
                tbl = f"{header_line}\n{separator_line}"
                sections.append(ExtractedSection(
                    content=tbl,
                    section_title=f"{file_path.stem} (Header)",
                    section_type="table",
                    metadata={"columns": headers, "row_count": 0}
                ))
            else:
                for idx in range(0, total_data_rows, self.batch_size):
                    batch = data_rows[idx : idx + self.batch_size]
                    start_num = idx + 1
                    end_num = idx + len(batch)

                    # Build markdown table carrying column headers
                    lines = [
                        "| " + " | ".join(headers) + " |",
                        "| " + " | ".join(["---"] * len(headers)) + " |"
                    ]
                    for row in batch:
                        # Pad or truncate row to header length
                        padded_row = row + [""] * max(0, len(headers) - len(row))
                        padded_row = padded_row[:len(headers)]
                        lines.append("| " + " | ".join(padded_row) + " |")

                    markdown_table = "\n".join(lines)
                    sections.append(ExtractedSection(
                        content=markdown_table,
                        section_title=f"{file_path.stem} (Rows {start_num}-{end_num})",
                        section_type="table",
                        metadata={
                            "columns": headers,
                            "start_row": start_num,
                            "end_row": end_num,
                            "total_rows": total_data_rows
                        }
                    ))
        else:
            sections.append(ExtractedSection(
                content="",
                section_title=file_path.stem,
                section_type="table",
                metadata={"columns": [], "total_rows": 0}
            ))

        return ExtractedDocument(
            doc_id=doc_id,
            file_path=str(file_path.resolve()),
            file_name=file_path.name,
            file_type="csv",
            file_size=file_path.stat().st_size,
            sections=sections,
            raw_text=text,
            metadata={
                "extension": ".csv",
                "columns": headers,
                "row_count": max(0, len(rows) - 1)
            }
        )
