import unittest
from unittest.mock import MagicMock

import numpy as np

from woofbook.config import DEFAULT_MODEL_WEIGHTS_PATH
from woofbook.tts_engine import TTSEngine


class TestTTSEngine(unittest.TestCase):
    def test_initialization_raises_value_error_for_unknown_voice(self):
        with self.assertRaises(ValueError):
            TTSEngine(voice="unsupported_voice")

    def test_initialization_raises_file_not_found_for_missing_weights(self):
        with self.assertRaises(FileNotFoundError):
            TTSEngine(model_weights_path="/nonexistent/path/weights.npz")

    def test_generate_silence_returns_zeros_with_exact_frame_count(self):
        tts_engine = TTSEngine(model_weights_path=DEFAULT_MODEL_WEIGHTS_PATH)
        silence_audio = tts_engine.generate_silence(duration_seconds=0.5)

        self.assertEqual(len(silence_audio), 12000)
        self.assertEqual(silence_audio.dtype, np.float32)
        self.assertTrue(np.all(silence_audio == 0.0))

    def test_synthesize_empty_string_returns_empty_array(self):
        tts_engine = TTSEngine(model_weights_path=DEFAULT_MODEL_WEIGHTS_PATH)
        synthesized_audio = tts_engine.synthesize("   ")

        self.assertEqual(len(synthesized_audio), 0)
        self.assertEqual(synthesized_audio.dtype, np.float32)

    def test_synthesize_paragraphs_includes_pause_and_executes_callback(self):
        tts_engine = TTSEngine(model_weights_path=DEFAULT_MODEL_WEIGHTS_PATH)
        tts_engine.woof_model = MagicMock(
            return_value=np.ones(2400, dtype=np.float32)
        )

        callback_events = []

        def recorded_callback(current_index: int, total_count: int, paragraph_text: str):
            callback_events.append((current_index, total_count, paragraph_text))

        paragraphs = ["First paragraph.", "", "Second paragraph."]
        result_audio = tts_engine.synthesize_paragraphs(
            paragraphs=paragraphs,
            pause_duration_seconds=0.1,
            progress_callback=recorded_callback,
        )

        self.assertEqual(len(callback_events), 2)
        self.assertEqual(callback_events[0], (1, 3, "First paragraph."))
        self.assertEqual(callback_events[1], (3, 3, "Second paragraph."))
        self.assertGreater(len(result_audio), 0)


if __name__ == "__main__":
    unittest.main()
