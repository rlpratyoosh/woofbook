import tempfile
import unittest
from pathlib import Path

from woofbook.pipeline import WoofbookPipeline, sanitize_filename


class TestWoofbookPipeline(unittest.TestCase):
    def setUp(self):
        self.temporary_test_directory = tempfile.TemporaryDirectory()
        self.output_directory_path = Path(self.temporary_test_directory.name)
        self.sample_pdf_path = Path("books/sample_book.pdf").resolve()

    def tearDown(self):
        self.temporary_test_directory.cleanup()

    def test_sanitize_filename_cleans_and_formats_strings(self):
        self.assertEqual(sanitize_filename("The Great Gatsby!"), "the_great_gatsby")
        self.assertEqual(sanitize_filename("  Chapter  #1: Intro  "), "chapter_1_intro")
        self.assertEqual(sanitize_filename("Alice's Adventures"), "alices_adventures")

    def test_pipeline_initialization_configures_output_directory(self):
        custom_target_directory = self.output_directory_path / "custom_output"
        pipeline = WoofbookPipeline(
            pdf_path=self.sample_pdf_path,
            output_directory=custom_target_directory,
        )

        self.assertEqual(pipeline.book_output_directory, custom_target_directory.resolve())
        self.assertTrue(pipeline.book_output_directory.exists())
        self.assertEqual(
            pipeline.checkpoint_manager.book_output_directory,
            custom_target_directory.resolve(),
        )

    def test_pipeline_list_chapters_delegation(self):
        pipeline = WoofbookPipeline(
            pdf_path=self.sample_pdf_path,
            output_directory=self.output_directory_path,
        )
        chapters = pipeline.list_chapters()

        self.assertGreaterEqual(len(chapters), 1)
        self.assertEqual(chapters[0].index, 1)

    def test_dry_run_export_text_generates_formatted_file(self):
        pipeline = WoofbookPipeline(
            pdf_path=self.sample_pdf_path,
            output_directory=self.output_directory_path,
        )
        destination_text_path = self.output_directory_path / "preview.txt"
        exported_path = pipeline.dry_run_export_text(destination_text_path)

        self.assertTrue(exported_path.exists())
        exported_content = exported_path.read_text(encoding="utf-8")
        self.assertIn("Book Title :", exported_content)
        self.assertIn("Source PDF :", exported_content)
        self.assertIn("### Chapter 1:", exported_content)


if __name__ == "__main__":
    unittest.main()
