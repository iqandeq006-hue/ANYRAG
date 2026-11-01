from pathlib import Path
from typing import List
from bs4 import BeautifulSoup, Tag
from .base import BaseParser, ExtractedDocument, ExtractedSection

class HTMLParser(BaseParser):
    """
    Dedicated HTML parser that strips boilerplate markup (scripts, styles, nav, footer)
    and extracts structured text grouped by headings, lists, and tables rather than
    dumping raw HTML tags.
    """

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
            soup = BeautifulSoup(text, "html.parser")
        except Exception:
            soup = BeautifulSoup(text, "html.parser")

        # Strip unneeded boilerplate elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form"]):
            tag.decompose()

        # Extract page title
        doc_title = soup.title.string.strip() if soup.title and soup.title.string else file_path.stem

        sections: List[ExtractedSection] = []

        # Find body or main container
        body = soup.body or soup

        # Heading-based structured extraction
        heading_tags = ["h1", "h2", "h3", "h4", "h5", "h6"]
        all_headings = body.find_all(heading_tags)

        if all_headings:
            # Check content before first heading
            pre_heading_content = []
            for elem in body.children:
                if isinstance(elem, Tag) and elem.name in heading_tags:
                    break
                if isinstance(elem, Tag):
                    t = self._render_tag_content(elem)
                    if t:
                        pre_heading_content.append(t)

            if pre_heading_content:
                sections.append(ExtractedSection(
                    content="\n\n".join(pre_heading_content).strip(),
                    section_title=f"{doc_title} (Overview)",
                    section_type="html_overview"
                ))

            # Process each heading and its following sibling content until next heading
            for h in all_headings:
                h_level = h.name
                h_title = h.get_text(" ", strip=True)
                if not h_title:
                    continue

                section_text_parts = [f"### {h_title}"]
                curr = h.next_sibling
                while curr:
                    if isinstance(curr, Tag):
                        if curr.name in heading_tags:
                            break
                        rendered = self._render_tag_content(curr)
                        if rendered:
                            section_text_parts.append(rendered)
                    curr = curr.next_sibling

                full_sec_text = "\n\n".join(section_text_parts).strip()
                sections.append(ExtractedSection(
                    content=full_sec_text,
                    section_title=h_title,
                    section_type="html_section",
                    metadata={"heading_level": h_level}
                ))
        else:
            # No headings found, extract structured blocks (paragraphs, lists, tables)
            blocks = []
            for child in body.children:
                if isinstance(child, Tag):
                    rendered = self._render_tag_content(child)
                    if rendered:
                        blocks.append(rendered)

            if blocks:
                # Group blocks into chunks of ~1500 chars
                curr_chunk = []
                curr_len = 0
                chunk_idx = 1
                for b in blocks:
                    curr_chunk.append(b)
                    curr_len += len(b)
                    if curr_len >= 1200:
                        sections.append(ExtractedSection(
                            content="\n\n".join(curr_chunk).strip(),
                            section_title=f"{doc_title} (Part {chunk_idx})",
                            section_type="html_block"
                        ))
                        curr_chunk = []
                        curr_len = 0
                        chunk_idx += 1
                if curr_chunk:
                    sections.append(ExtractedSection(
                        content="\n\n".join(curr_chunk).strip(),
                        section_title=f"{doc_title} (Part {chunk_idx})",
                        section_type="html_block"
                    ))
            else:
                plain = soup.get_text("\n", strip=True)
                sections.append(ExtractedSection(
                    content=plain,
                    section_title=doc_title,
                    section_type="text"
                ))

        clean_raw_text = "\n\n".join(s.content for s in sections)

        return ExtractedDocument(
            doc_id=doc_id,
            file_path=str(file_path.resolve()),
            file_name=file_path.name,
            file_type="html",
            file_size=file_path.stat().st_size,
            sections=sections,
            raw_text=clean_raw_text,
            metadata={
                "extension": file_path.suffix.lower(),
                "title": doc_title,
                "section_count": len(sections)
            }
        )

    def _render_tag_content(self, tag: Tag) -> str:
        """Render Tag into structured Markdown (handling lists, tables, paragraphs, pre)."""
        name = tag.name.lower() if tag.name else ""

        # Tables -> Markdown table
        if name == "table":
            rows = []
            for tr in tag.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                if cells:
                    rows.append(cells)
            if rows:
                max_cols = max(len(r) for r in rows)
                header = rows[0] + [""] * (max_cols - len(rows[0]))
                md_lines = [
                    "| " + " | ".join(header) + " |",
                    "| " + " | ".join(["---"] * max_cols) + " |"
                ]
                for r in rows[1:]:
                    padded = r + [""] * (max_cols - len(r))
                    md_lines.append("| " + " | ".join(padded) + " |")
                return "\n".join(md_lines)
            return ""

        # Lists -> Markdown bullet items
        if name in ["ul", "ol"]:
            items = []
            for idx, li in enumerate(tag.find_all("li", recursive=False), 1):
                txt = li.get_text(" ", strip=True)
                if txt:
                    prefix = f"{idx}." if name == "ol" else "-"
                    items.append(f"{prefix} {txt}")
            return "\n".join(items)

        # Code blocks
        if name in ["pre", "code"]:
            code_text = tag.get_text(strip=True)
            return f"```\n{code_text}\n```" if code_text else ""

        # Standard paragraph or div
        text = tag.get_text(" ", strip=True)
        return text if text else ""
