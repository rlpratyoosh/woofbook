import tempfile
import unittest
from pathlib import Path

from audiobook.checkpoint_manager import CheckpointManager


class TestCheckpointManager(unittest.TestCase):
    def setUp(self):
        self.temporary_test_directory = tempfile.TemporaryDirectory()
        self.output_directory_path = Path(self.temporary_test_directory.name)
        self.checkpoint_manager = CheckpointManager(self.output_directory_path)

    def tearDown(self):
        self.temporary_test_directory.cleanup()

    def test_checkpoint_initial_state(self):
        self.assertEqual(self.checkpoint_manager.checkpoint_data, {"completed_chapters": {}})
        self.assertFalse(self.checkpoint_manager.is_chapter_completed(1))

    def test_record_chapter_completion_and_query_status(self):
        dummy_audio_file = self.output_directory_path / "Chapter_01_test.mp3"
        dummy_audio_file.write_bytes(b"dummy_audio_content")

        self.checkpoint_manager.record_chapter_completion(
            chapter_index=1,
            audio_file_path=dummy_audio_file,
            chapter_title="Test Chapter Title",
        )

        self.assertTrue(self.checkpoint_manager.is_chapter_completed(1))
        self.assertFalse(self.checkpoint_manager.is_chapter_completed(2))

        completed_file_path = self.checkpoint_manager.get_completed_chapter_file_path(1)
        self.assertEqual(completed_file_path, dummy_audio_file.resolve())

    def test_is_chapter_completed_returns_false_when_file_is_missing_or_empty(self):
        nonexistent_audio_file = self.output_directory_path / "nonexistent.mp3"
        self.checkpoint_manager.record_chapter_completion(
            chapter_index=1,
            audio_file_path=nonexistent_audio_file,
            chapter_title="Missing File Chapter",
        )
        self.assertFalse(self.checkpoint_manager.is_chapter_completed(1))

        empty_audio_file = self.output_directory_path / "empty.mp3"
        empty_audio_file.write_bytes(b"")
        self.checkpoint_manager.record_chapter_completion(
            chapter_index=2,
            audio_file_path=empty_audio_file,
            chapter_title="Empty File Chapter",
        )
        self.assertFalse(self.checkpoint_manager.is_chapter_completed(2))

    def test_clear_checkpoints_removes_recorded_chapters(self):
        dummy_audio_file = self.output_directory_path / "Chapter_01.mp3"
        dummy_audio_file.write_bytes(b"content")
        self.checkpoint_manager.record_chapter_completion(
            chapter_index=1,
            audio_file_path=dummy_audio_file,
            chapter_title="Chapter 1",
        )

        self.assertTrue(self.checkpoint_manager.is_chapter_completed(1))
        self.checkpoint_manager.clear_checkpoints()
        self.assertFalse(self.checkpoint_manager.is_chapter_completed(1))

    def test_load_checkpoint_handles_corrupted_json_file(self):
        self.checkpoint_manager.checkpoint_file_path.write_text("invalid json content {{{")
        fresh_checkpoint_manager = CheckpointManager(self.output_directory_path)
        self.assertEqual(fresh_checkpoint_manager.checkpoint_data, {"completed_chapters": {}})


if __name__ == "__main__":
    unittest.main()
