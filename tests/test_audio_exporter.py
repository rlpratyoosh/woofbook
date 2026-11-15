import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from audiobook.audio_exporter import AudioExporter


class TestAudioExporter(unittest.TestCase):
    def setUp(self):
        self.temporary_test_directory = tempfile.TemporaryDirectory()
        self.output_directory_path = Path(self.temporary_test_directory.name)
        self.audio_exporter = AudioExporter(sample_rate=24000)

    def tearDown(self):
        self.temporary_test_directory.cleanup()

    def test_convert_float_to_pcm16_scaling_and_clipping(self):
        input_audio_samples = np.array([-2.0, -1.0, 0.0, 0.5, 1.0, 2.0], dtype=np.float32)
        pcm_result = self.audio_exporter.convert_float_to_pcm16(input_audio_samples)

        self.assertEqual(pcm_result.dtype, np.dtype("<i2"))
        self.assertEqual(pcm_result[0], -32767)
        self.assertEqual(pcm_result[1], -32767)
        self.assertEqual(pcm_result[2], 0)
        self.assertEqual(pcm_result[3], 16384)
        self.assertEqual(pcm_result[4], 32767)
        self.assertEqual(pcm_result[5], 32767)

    def test_save_wav_creates_valid_wave_file(self):
        test_samples = np.zeros(24000, dtype=np.float32)
        destination_wav_path = self.output_directory_path / "output_test.wav"

        saved_wav_path = self.audio_exporter.save_wav(destination_wav_path, test_samples)
        self.assertTrue(saved_wav_path.exists())

        with wave.open(str(saved_wav_path), "rb") as opened_wav_file:
            self.assertEqual(opened_wav_file.getnchannels(), 1)
            self.assertEqual(opened_wav_file.getsampwidth(), 2)
            self.assertEqual(opened_wav_file.getframerate(), 24000)
            self.assertEqual(opened_wav_file.getnframes(), 24000)

    def test_export_wav_format(self):
        test_samples = np.zeros(12000, dtype=np.float32)
        destination_path = self.output_directory_path / "exported.wav"

        exported_path = self.audio_exporter.export(
            audio_samples=test_samples,
            output_path=destination_path,
            audio_format="wav",
        )
        self.assertTrue(exported_path.exists())

        with wave.open(str(exported_path), "rb") as opened_wav_file:
            self.assertEqual(opened_wav_file.getnframes(), 12000)

    def test_export_mp3_format(self):
        test_samples = np.zeros(12000, dtype=np.float32)
        destination_path = self.output_directory_path / "exported.mp3"

        exported_path = self.audio_exporter.export(
            audio_samples=test_samples,
            output_path=destination_path,
            audio_format="mp3",
            metadata={"title": "Test Title", "artist": "Test Artist"},
        )
        self.assertTrue(exported_path.exists())
        self.assertGreater(exported_path.stat().st_size, 0)

    def test_merge_audio_files_raises_error_when_given_empty_list(self):
        with self.assertRaises(ValueError):
            self.audio_exporter.merge_audio_files(
                input_audio_paths=[],
                output_path=self.output_directory_path / "merged.mp3",
            )

    def test_merge_audio_files_single_file_shortcut(self):
        source_audio_file = self.output_directory_path / "single_source.mp3"
        source_audio_file.write_bytes(b"sample_binary_audio_data")

        merged_output_path = self.output_directory_path / "merged_shortcut.mp3"
        result_path = self.audio_exporter.merge_audio_files(
            input_audio_paths=[source_audio_file],
            output_path=merged_output_path,
            silence_between_files_seconds=0.0,
        )

        self.assertTrue(result_path.exists())
        self.assertEqual(result_path.read_bytes(), b"sample_binary_audio_data")

    def test_merge_multiple_audio_files_with_silence_interval(self):
        first_audio_samples = np.zeros(12000, dtype=np.float32)
        second_audio_samples = np.zeros(12000, dtype=np.float32)

        first_wav_file = self.audio_exporter.save_wav(
            self.output_directory_path / "first_segment.wav", first_audio_samples
        )
        second_wav_file = self.audio_exporter.save_wav(
            self.output_directory_path / "second_segment.wav", second_audio_samples
        )

        merged_master_path = self.output_directory_path / "merged_master.mp3"
        result_master_path = self.audio_exporter.merge_audio_files(
            input_audio_paths=[first_wav_file, second_wav_file],
            output_path=merged_master_path,
            silence_between_files_seconds=0.5,
            audio_format="mp3",
        )

        self.assertTrue(result_master_path.exists())
        self.assertGreater(result_master_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
