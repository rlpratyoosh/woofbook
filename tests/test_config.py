import os
import unittest
from pathlib import Path

from woofbook.config import (
    AUDIO_SAMPLE_RATE,
    AVAILABLE_VOICES,
    DEFAULT_AUDIO_BITRATE,
    DEFAULT_AUDIO_OUTPUT_DIRECTORY,
    DEFAULT_BOOKS_DIRECTORY,
    DEFAULT_CHAPTER_PAUSE_SECONDS,
    DEFAULT_END_OF_SPEECH_THRESHOLD,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL_DIRECTORY,
    DEFAULT_MODEL_WEIGHTS_PATH,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_PARAGRAPH_PAUSE_SECONDS,
    DEFAULT_SYNTHESIS_TEMPERATURE,
    DEFAULT_VOICE,
)


class TestConfigurationDefaults(unittest.TestCase):
    def test_default_sample_rate_and_format(self):
        self.assertEqual(AUDIO_SAMPLE_RATE, 24000)
        self.assertEqual(DEFAULT_OUTPUT_FORMAT, "mp3")
        self.assertEqual(DEFAULT_AUDIO_BITRATE, "128k")

    def test_default_voices_configuration(self):
        self.assertIn("juno", AVAILABLE_VOICES)
        self.assertIn("mira", AVAILABLE_VOICES)
        self.assertEqual(DEFAULT_VOICE, "juno")

    def test_default_pause_intervals(self):
        self.assertEqual(DEFAULT_PARAGRAPH_PAUSE_SECONDS, 0.45)
        self.assertEqual(DEFAULT_CHAPTER_PAUSE_SECONDS, 2.0)

    def test_default_synthesis_parameters(self):
        self.assertEqual(DEFAULT_SYNTHESIS_TEMPERATURE, 0.5)
        self.assertEqual(DEFAULT_END_OF_SPEECH_THRESHOLD, 0.9)
        self.assertEqual(DEFAULT_MAX_RETRIES, 3)

    def test_default_directories_are_path_instances(self):
        self.assertIsInstance(DEFAULT_BOOKS_DIRECTORY, Path)
        self.assertIsInstance(DEFAULT_AUDIO_OUTPUT_DIRECTORY, Path)


if __name__ == "__main__":
    unittest.main()
