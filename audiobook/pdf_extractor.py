import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

POPPLER_PAGE_DELIMITER = "\x0c"

LIGATURE_REPLACEMENTS = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
    "—": " -- ",
    "–": "-",
    "…": "...",
}

STANDALONE_PAGE_NUMBER_PATTERN = re.compile(r"^[-–—\[\(]?\s*\d+\s*[-–—\]\)]?$")
HYPHENATED_LINE_BREAK_PATTERN = re.compile(r"(\b[a-zA-Z]{2,})-\s+([a-zA-Z]{2,}\b)")
WHITESPACE_NORMALIZATION_PATTERN = re.compile(r"\s+")

CHAPTER_HEADING_PATTERN = re.compile(
    r"^(?:"
    r"(?:\d+[\.\)]\s*)?(?:chapter|book|part|act|section)\s+(?:[0-9]+|[ivxlcdm]+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
    r"|(?:prologue|epilogue|introduction|preface|foreword|afterword|conclusion)"
    r")\b.*$",
    re.IGNORECASE,
)


@dataclass
class Chapter:
    title: str
    index: int
    start_page: int
    end_page: int
    paragraphs: List[str] = field(default_factory=list)

    @property
    def total_words(self) -> int:
        return sum(len(paragraph.split()) for paragraph in self.paragraphs)

    @property
    def total_chars(self) -> int:
        return sum(len(paragraph) for paragraph in self.paragraphs)


@dataclass
class _DetectedBookSection:
    start_page: int
    end_page: int
    title: str
    paragraphs: List[str]


class PDFExtractor:
    CHAPTER_HEADING_PATTERN = CHAPTER_HEADING_PATTERN
    CHAPTER_REGEX = CHAPTER_HEADING_PATTERN

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path).resolve()
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

        self.pdftotext_executable_path = shutil.which("pdftotext")
        self.pdfinfo_executable_path = shutil.which("pdfinfo")

        if not self.pdftotext_executable_path:
            raise RuntimeError(
                "pdftotext binary not found. Please install poppler-utils (e.g. sudo apt install poppler-utils)."
            )

    def get_metadata(self) -> dict:
        metadata = {
            "title": self.pdf_path.stem.replace("_", " ").title(),
            "author": "Unknown Author",
            "pages": 0,
        }

        if not self.pdfinfo_executable_path:
            extracted_pages = self.extract_raw_pages()
            metadata["pages"] = len(extracted_pages)
            return metadata

        try:
            completed_process = subprocess.run(
                [self.pdfinfo_executable_path, str(self.pdf_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in completed_process.stdout.splitlines():
                if ":" not in line:
                    continue
                header_key, header_value = line.split(":", 1)
                header_key = header_key.strip().lower()
                header_value = header_value.strip()
                if header_key == "pages" and header_value.isdigit():
                    metadata["pages"] = int(header_value)
                elif header_key == "title" and header_value:
                    metadata["title"] = header_value
                elif header_key == "author" and header_value:
                    metadata["author"] = header_value
        except Exception:
            extracted_pages = self.extract_raw_pages()
            metadata["pages"] = len(extracted_pages)

        return metadata

    def extract_raw_pages(
        self, start_page: int = 1, end_page: Optional[int] = None
    ) -> List[Tuple[int, str]]:
        extraction_command = [self.pdftotext_executable_path, "-layout", "-remove-hyphens", "all"]
        if start_page > 1:
            extraction_command.extend(["-f", str(start_page)])
        if end_page is not None:
            extraction_command.extend(["-l", str(end_page)])

        extraction_command.extend([str(self.pdf_path), "-"])

        completed_process = subprocess.run(
            extraction_command,
            capture_output=True,
            text=True,
            check=True,
        )
        raw_page_texts = completed_process.stdout.split(POPPLER_PAGE_DELIMITER)

        extracted_pages = []
        current_page_number = start_page
        for page_text in raw_page_texts:
            if not page_text and current_page_number > (end_page or current_page_number):
                continue
            extracted_pages.append((current_page_number, page_text))
            current_page_number += 1

        return extracted_pages

    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        cleaned_text = raw_text
        for ligature, replacement in LIGATURE_REPLACEMENTS.items():
            cleaned_text = cleaned_text.replace(ligature, replacement)

        filtered_lines = []
        for line in cleaned_text.splitlines():
            stripped_line = line.strip()
            if STANDALONE_PAGE_NUMBER_PATTERN.match(stripped_line):
                continue
            filtered_lines.append(line)

        cleaned_paragraphs = []
        accumulated_paragraph_lines = []

        def commit_current_paragraph():
            nonlocal accumulated_paragraph_lines
            if accumulated_paragraph_lines:
                merged_line_text = " ".join(accumulated_paragraph_lines)
                dehyphenated_text = HYPHENATED_LINE_BREAK_PATTERN.sub(r"\1\2", merged_line_text)
                normalized_text = WHITESPACE_NORMALIZATION_PATTERN.sub(" ", dehyphenated_text).strip()
                if normalized_text:
                    cleaned_paragraphs.append(normalized_text)
                accumulated_paragraph_lines = []

        for line in filtered_lines:
            stripped_line = line.strip()
            if not stripped_line:
                commit_current_paragraph()
            elif cls.CHAPTER_HEADING_PATTERN.match(stripped_line):
                commit_current_paragraph()
                cleaned_heading = WHITESPACE_NORMALIZATION_PATTERN.sub(" ", stripped_line).strip()
                cleaned_paragraphs.append(cleaned_heading)
            else:
                accumulated_paragraph_lines.append(stripped_line)

        commit_current_paragraph()
        return "\n\n".join(cleaned_paragraphs)

    def extract_chapters(
        self, start_page: int = 1, end_page: Optional[int] = None
    ) -> List[Chapter]:
        raw_pages = self.extract_raw_pages(start_page, end_page)

        detected_sections: List[_DetectedBookSection] = []
        current_title = None
        current_start_page = start_page
        current_paragraphs = []

        for page_number, raw_content in raw_pages:
            cleaned_content = self.clean_text(raw_content)
            if not cleaned_content.strip():
                continue

            page_paragraphs = [
                paragraph.strip()
                for paragraph in cleaned_content.split("\n\n")
                if paragraph.strip()
            ]

            for paragraph in page_paragraphs:
                first_line = paragraph.splitlines()[0].strip()
                if len(first_line) < 120 and self.CHAPTER_HEADING_PATTERN.match(first_line):
                    if current_paragraphs:
                        section_title = current_title or (
                            f"Chapter {len(detected_sections) + 1}"
                            if detected_sections
                            else "Opening / Front Matter"
                        )
                        detected_sections.append(
                            _DetectedBookSection(
                                start_page=current_start_page,
                                end_page=page_number - 1,
                                title=section_title,
                                paragraphs=current_paragraphs,
                            )
                        )
                        current_paragraphs = []
                    current_title = first_line
                    current_start_page = page_number
                    remaining_text = paragraph[len(first_line):].strip()
                    if remaining_text:
                        current_paragraphs.append(remaining_text)
                else:
                    current_paragraphs.append(paragraph)

        if current_paragraphs:
            section_title = current_title or (
                f"Chapter {len(detected_sections) + 1}"
                if detected_sections
                else "Full Book"
            )
            detected_sections.append(
                _DetectedBookSection(
                    start_page=current_start_page,
                    end_page=raw_pages[-1][0],
                    title=section_title,
                    paragraphs=current_paragraphs,
                )
            )

        if not detected_sections:
            return []

        if len(detected_sections) == 1 and detected_sections[0].title == "Full Book":
            single_section = detected_sections[0]
            total_pages = single_section.end_page - single_section.start_page + 1
            if total_pages > 25:
                pages_per_chunk = 15
                estimated_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
                paragraphs_per_chunk = max(1, len(single_section.paragraphs) // estimated_chunks)
                chapters = []
                chunk_index = 1
                for offset in range(0, len(single_section.paragraphs), paragraphs_per_chunk):
                    chunk_paragraphs = single_section.paragraphs[offset : offset + paragraphs_per_chunk]
                    chunk_start_page = single_section.start_page + (
                        offset // max(1, len(single_section.paragraphs) // total_pages)
                    )
                    chunk_end_page = min(single_section.end_page, chunk_start_page + pages_per_chunk - 1)
                    chapters.append(
                        Chapter(
                            title=f"Section {chunk_index} (Pages {chunk_start_page}-{chunk_end_page})",
                            index=chunk_index,
                            start_page=chunk_start_page,
                            end_page=chunk_end_page,
                            paragraphs=chunk_paragraphs,
                        )
                    )
                    chunk_index += 1
                return chapters

        chapters = []
        for chapter_index, section in enumerate(detected_sections, start=1):
            chapters.append(
                Chapter(
                    title=section.title,
                    index=chapter_index,
                    start_page=section.start_page,
                    end_page=max(section.start_page, section.end_page),
                    paragraphs=section.paragraphs,
                )
            )

        return chapters
