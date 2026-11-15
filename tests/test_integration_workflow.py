import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from woofbook.pipeline import WoofbookPipeline


class TestWoofbookWorkflowIntegration(unittest.TestCase):
    def setUp(self):
        self.temporary_test_directory = tempfile.TemporaryDirectory()
        self.output_directory_path = Path(self.temporary_test_directory.name)
        self.sample_pdf_path = Path("books/sample_book.pdf").resolve()

    def tearDown(self):
        self.temporary_test_directory.cleanup()

    def test_full_pipeline_run_generates_chapters_and_master_audiobook(self):
        pipeline = WoofbookPipeline(
            pdf_path=self.sample_pdf_path,
            output_directory=self.output_directory_path,
            audio_format="mp3",
        )

        pipeline._tts_engine = MagicMock()
        pipeline._tts_engine.synthesize_paragraphs.return_value = np.zeros(12000, dtype=np.float32)

        execution_summary = pipeline.run(merge_master=True)

        self.assertEqual(execution_summary["status"], "success")
        self.assertGreaterEqual(len(execution_summary["chapters"]), 1)
        self.assertIsNotNone(execution_summary["master_file"])

        for chapter_file_path in execution_summary["chapters"]:
            self.assertTrue(chapter_file_path.exists())
            self.assertGreater(chapter_file_path.stat().st_size, 0)

        master_file_path = execution_summary["master_file"]
        self.assertTrue(master_file_path.exists())
        self.assertGreater(master_file_path.stat().st_size, 0)

        for chapter_index in range(1, len(execution_summary["chapters"]) + 1):
            self.assertTrue(pipeline.checkpoint_manager.is_chapter_completed(chapter_index))

    def test_checkpoint_resumption_skips_already_completed_chapters(self):
        pipeline = WoofbookPipeline(
            pdf_path=self.sample_pdf_path,
            output_directory=self.output_directory_path,
            audio_format="mp3",
        )

        pipeline._tts_engine = MagicMock()
        pipeline._tts_engine.synthesize_paragraphs.return_value = np.zeros(12000, dtype=np.float32)

        first_run_summary = pipeline.run(merge_master=False)
        self.assertEqual(pipeline._tts_engine.synthesize_paragraphs.call_count, len(first_run_summary["chapters"]))

        pipeline._tts_engine.synthesize_paragraphs.reset_mock()
        second_run_summary = pipeline.run(merge_master=False)

        self.assertEqual(pipeline._tts_engine.synthesize_paragraphs.call_count, 0)
        self.assertEqual(len(second_run_summary["chapters"]), len(first_run_summary["chapters"]))

    def test_force_regeneration_clears_checkpoints_and_resynthesizes(self):
        pipeline = WoofbookPipeline(
            pdf_path=self.sample_pdf_path,
            output_directory=self.output_directory_path,
            audio_format="mp3",
        )
        pipeline._tts_engine = MagicMock()
        pipeline._tts_engine.synthesize_paragraphs.return_value = np.zeros(12000, dtype=np.float32)
        pipeline.run(merge_master=False)

        forced_pipeline = WoofbookPipeline(
            pdf_path=self.sample_pdf_path,
            output_directory=self.output_directory_path,
            audio_format="mp3",
            force_regeneration=True,
        )
        forced_pipeline._tts_engine = MagicMock()
        forced_pipeline._tts_engine.synthesize_paragraphs.return_value = np.zeros(12000, dtype=np.float32)
        forced_run_summary = forced_pipeline.run(merge_master=False)

        self.assertGreater(forced_pipeline._tts_engine.synthesize_paragraphs.call_count, 0)
        self.assertGreaterEqual(len(forced_run_summary["chapters"]), 1)

    def test_cli_list_chapters_command(self):
        completed_process = subprocess.run(
            [sys.executable, "main.py", str(self.sample_pdf_path), "--list-chapters"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Detected", completed_process.stdout)
        self.assertIn("chapter(s)", completed_process.stdout)
        self.assertIn("Chapter 01", completed_process.stdout)

    def test_cli_dry_run_command(self):
        custom_dry_run_dir = self.output_directory_path / "cli_dry_run"
        completed_process = subprocess.run(
            [
                sys.executable,
                "main.py",
                str(self.sample_pdf_path),
                "--dry-run",
                "-o",
                str(custom_dry_run_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Dry run completed", completed_process.stdout)
        exported_txt_files = list(custom_dry_run_dir.glob("*.txt"))
        self.assertEqual(len(exported_txt_files), 1)

    def test_cli_missing_pdf_file_exits_with_error(self):
        completed_process = subprocess.run(
            [sys.executable, "main.py", "nonexistent_book.pdf"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed_process.returncode, 0)
        self.assertIn("Error: File not found", completed_process.stderr)


if __name__ == "__main__":
    unittest.main()
