import ast
import re
from pathlib import Path
from typing import List, Optional
from .base import BaseParser, ExtractedDocument, ExtractedSection

class CodeParser(BaseParser):
    """
    Dedicated code parser. For Python (.py), parses the AST to split by class and function
    boundaries, preventing functions or methods from being sliced in half mid-body.
    Provides regex/indentation boundary splitting for non-Python or syntax-invalid code.
    """

    def parse(self, file_path: Path) -> ExtractedDocument:
        doc_id = ExtractedDocument.generate_id(file_path)
        ext = file_path.suffix.lower()

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

        lines = text.splitlines(keepends=True)
        sections: List[ExtractedSection] = []

        if ext == ".py":
            sections = self._parse_python(file_path, text, lines)
        else:
            sections = self._parse_generic_code(file_path, text, lines)

        if not sections:
            sections.append(ExtractedSection(
                content=text.strip(),
                section_title=file_path.stem,
                section_type="code"
            ))

        return ExtractedDocument(
            doc_id=doc_id,
            file_path=str(file_path.resolve()),
            file_name=file_path.name,
            file_type=ext.lstrip(".") or "code",
            file_size=file_path.stat().st_size,
            sections=sections,
            raw_text=text,
            metadata={
                "extension": ext,
                "language": "python" if ext == ".py" else "code",
                "line_count": len(lines),
                "section_count": len(sections)
            }
        )

    def _parse_python(self, file_path: Path, text: str, lines: List[str]) -> List[ExtractedSection]:
        try:
            tree = ast.parse(text, filename=file_path.name)
        except SyntaxError:
            # Fallback to generic code splitting if file has syntax errors
            return self._parse_generic_code(file_path, text, lines)

        sections: List[ExtractedSection] = []
        file_stem = file_path.stem

        # Track top-level statements for module-level setup/imports
        setup_lines: List[str] = []
        covered_line_ranges = []

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                covered_line_ranges.append((start, end))
                fn_code = "".join(lines[start - 1 : end]).strip()
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                sections.append(ExtractedSection(
                    content=fn_code,
                    section_title=f"{file_stem} > {prefix} {node.name}()",
                    section_type="code_function",
                    metadata={"name": node.name, "type": "function", "start_line": start, "end_line": end}
                ))

            elif isinstance(node, ast.ClassDef):
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                covered_line_ranges.append((start, end))

                # Check methods inside class
                methods = [m for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                class_header_lines = []

                # Extract class docstring and class-level fields before first method
                first_method_line = methods[0].lineno if methods else end + 1
                class_header = "".join(lines[start - 1 : first_method_line - 1]).strip()
                if class_header:
                    sections.append(ExtractedSection(
                        content=class_header,
                        section_title=f"{file_stem} > class {node.name} (Definition & Attributes)",
                        section_type="code_class",
                        metadata={"name": node.name, "type": "class_header", "start_line": start, "end_line": first_method_line - 1}
                    ))

                for m in methods:
                    m_start = m.lineno
                    m_end = getattr(m, "end_lineno", m_start)
                    m_code = "".join(lines[m_start - 1 : m_end]).strip()
                    m_prefix = "async def" if isinstance(m, ast.AsyncFunctionDef) else "def"
                    sections.append(ExtractedSection(
                        content=f"# Inside class {node.name}:\n{m_code}",
                        section_title=f"{file_stem} > class {node.name}.{m.name}()",
                        section_type="code_method",
                        metadata={
                            "class": node.name,
                            "name": m.name,
                            "type": "method",
                            "start_line": m_start,
                            "end_line": m_end
                        }
                    ))

            else:
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                setup_lines.extend(lines[start - 1 : end])

        # If there are module-level imports/constants, add as first section
        setup_text = "".join(setup_lines).strip()
        if setup_text:
            sections.insert(0, ExtractedSection(
                content=setup_text,
                section_title=f"{file_stem} > Module Setup & Imports",
                section_type="code_setup",
                metadata={"type": "module_setup"}
            ))

        return sections

    def _parse_generic_code(self, file_path: Path, text: str, lines: List[str]) -> List[ExtractedSection]:
        """Boundary splitting based on function/class definitions for non-Python or syntax-broken code."""
        pattern = re.compile(r"^(?:(?:pub|public|private|protected|async|export|default)\s+)*(?:def|function|class|fn|struct|interface)\s+([A-Za-z0-9_]+)", re.MULTILINE)
        matches = list(pattern.finditer(text))

        if not matches:
            return [ExtractedSection(
                content=text.strip(),
                section_title=file_path.stem,
                section_type="code"
            )]

        sections: List[ExtractedSection] = []
        file_stem = file_path.stem

        # Leading header / imports
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()].strip()
            if preamble:
                sections.append(ExtractedSection(
                    content=preamble,
                    section_title=f"{file_stem} > Imports & Setup",
                    section_type="code_setup"
                ))

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[start:end].strip()
            decl_name = match.group(1)
            sections.append(ExtractedSection(
                content=block,
                section_title=f"{file_stem} > {decl_name}",
                section_type="code_block",
                metadata={"identifier": decl_name}
            ))

        return sections
