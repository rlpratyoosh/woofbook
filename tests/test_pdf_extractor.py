import unittest
from pathlib import Path

from audiobook.pdf_extractor import Chapter, PDFExtractor


class TestPDFExtractor(unittest.TestCase):
    def setUp(self):
        self.sample_book_path = Path("books/sample_book.pdf").resolve()

    def test_chapter_dataclass_metrics(self):
        chapter = Chapter(
            title="Chapter 1",
            index=1,
            start_page=1,
            end_page=3,
            paragraphs=["Hello world of audiobooks.", "Testing paragraph length."],
        )
        self.assertEqual(chapter.total_words, 7)
        self.assertEqual(chapter.total_chars, 51)

    def test_clean_text_ligature_replacements(self):
        raw_text_with_ligatures = "ﬁrst ﬂight of the ﬃ and ﬄ with ’curly‘ and “quotes” — emdash – endash…"
        cleaned_text = PDFExtractor.clean_text(raw_text_with_ligatures)

        self.assertIn("first", cleaned_text)
        self.assertIn("flight", cleaned_text)
        self.assertIn("ffi", cleaned_text)
        self.assertIn("ffl", cleaned_text)
        self.assertIn("'curly'", cleaned_text)
        self.assertIn('"quotes"', cleaned_text)
        self.assertIn(" -- ", cleaned_text)
        self.assertIn("-", cleaned_text)
        self.assertIn("...", cleaned_text)

    def test_clean_text_removes_standalone_page_numbers(self):
        raw_text_with_page_numbers = "Header line\n12\nFirst paragraph text.\n- 13 -\nSecond paragraph text.\n[14]"
        cleaned_text = PDFExtractor.clean_text(raw_text_with_page_numbers)

        self.assertNotIn("\n12\n", cleaned_text)
        self.assertNotIn("- 13 -", cleaned_text)
        self.assertNotIn("[14]", cleaned_text)
        self.assertIn("First paragraph text.", cleaned_text)
        self.assertIn("Second paragraph text.", cleaned_text)

    def test_clean_text_joins_hyphenated_line_breaks(self):
        raw_text_with_hyphenated_break = "This was an extra-\nordinary discovery made by the researcher."
        cleaned_text = PDFExtractor.clean_text(raw_text_with_hyphenated_break)

        self.assertIn("extraordinary", cleaned_text)
        self.assertNotIn("extra- ordinary", cleaned_text)

    def test_clean_text_isolates_chapter_headings(self):
        raw_text = "Introduction text.\n\nChapter 1 The Beginning\n\nOnce upon a time in a distant land."
        cleaned_text = PDFExtractor.clean_text(raw_text)
        paragraphs = cleaned_text.split("\n\n")

        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(paragraphs[1], "Chapter 1 The Beginning")

    def test_extract_metadata_from_existing_pdf(self):
        extractor = PDFExtractor(self.sample_book_path)
        metadata = extractor.get_metadata()

        self.assertIn("title", metadata)
        self.assertIn("author", metadata)
        self.assertIn("pages", metadata)
        self.assertGreaterEqual(metadata["pages"], 1)

    def test_extract_raw_pages_from_existing_pdf(self):
        extractor = PDFExtractor(self.sample_book_path)
        pages = extractor.extract_raw_pages()

        self.assertGreaterEqual(len(pages), 1)
        page_number, page_content = pages[0]
        self.assertEqual(page_number, 1)
        self.assertIn("Watson", page_content)

    def test_extract_chapters_from_existing_pdf(self):
        extractor = PDFExtractor(self.sample_book_path)
        chapters = extractor.extract_chapters()

        self.assertGreaterEqual(len(chapters), 1)
        first_chapter = chapters[0]
        self.assertEqual(first_chapter.index, 1)
        self.assertGreaterEqual(len(first_chapter.paragraphs), 1)

    def test_initialization_raises_error_for_nonexistent_pdf(self):
        with self.assertRaises(FileNotFoundError):
            PDFExtractor("books/nonexistent_file_path.pdf")


if __name__ == "__main__":
    unittest.main()
