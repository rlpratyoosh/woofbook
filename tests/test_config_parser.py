import os
import tempfile
import unittest
from pathlib import Path

from woofbook.config_parser import (
    WoofbookConfiguration,
    find_config_toml_path,
    parse_config_toml,
)
import woofbook.config as config


class TestConfigParser(unittest.TestCase):
    def setUp(self):
        self.temporary_test_directory = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temporary_test_directory.name)

    def tearDown(self):
        self.temporary_test_directory.cleanup()

    def test_default_configuration_values(self):
        default_config = WoofbookConfiguration()
        self.assertEqual(default_config.voice, "juno")
        self.assertEqual(default_config.output_format, "mp3")
        self.assertEqual(default_config.sample_rate, 24000)
        self.assertEqual(default_config.paragraph_pause_seconds, 0.45)
        self.assertEqual(default_config.chapter_pause_seconds, 2.0)
        self.assertEqual(default_config.synthesis_temperature, 0.5)
        self.assertEqual(default_config.end_of_speech_threshold, 0.9)
        self.assertEqual(default_config.max_retries, 3)
        self.assertEqual(default_config.audio_output_directory, Path("output").resolve())

    def test_parse_sectioned_toml_file(self):
        custom_toml_path = self.base_path / "custom_config.toml"
        custom_toml_content = """
[model]
model_directory = "./models"
weights_path = "./models/custom_weights.npz"
voice = "mira"
temperature = 0.7
end_of_speech_threshold = 0.85
max_retries = 5

[audio]
format = "wav"
bitrate = "192k"
sample_rate = 24000
paragraph_pause_seconds = 0.6
chapter_pause_seconds = 3.0

[paths]
books_directory = "./custom_books"
audio_output_directory = "./custom_audio"
"""
        custom_toml_path.write_text(custom_toml_content, encoding="utf-8")
        parsed_config = parse_config_toml(custom_toml_path)

        self.assertEqual(parsed_config.voice, "mira")
        self.assertEqual(parsed_config.output_format, "wav")
        self.assertEqual(parsed_config.audio_bitrate, "192k")
        self.assertEqual(parsed_config.paragraph_pause_seconds, 0.6)
        self.assertEqual(parsed_config.chapter_pause_seconds, 3.0)
        self.assertEqual(parsed_config.synthesis_temperature, 0.7)
        self.assertEqual(parsed_config.end_of_speech_threshold, 0.85)
        self.assertEqual(parsed_config.max_retries, 5)
        self.assertEqual(
            parsed_config.books_directory,
            (self.base_path / "custom_books").resolve(),
        )
        self.assertEqual(
            parsed_config.audio_output_directory,
            (self.base_path / "custom_audio").resolve(),
        )

    def test_parse_flat_top_level_toml_file(self):
        custom_toml_path = self.base_path / "flat_config.toml"
        custom_toml_content = """
voice = "mira"
output_format = "wav"
paragraph_pause_seconds = 1.0
temperature = 0.65
"""
        custom_toml_path.write_text(custom_toml_content, encoding="utf-8")
        parsed_config = parse_config_toml(custom_toml_path)

        self.assertEqual(parsed_config.voice, "mira")
        self.assertEqual(parsed_config.output_format, "wav")
        self.assertEqual(parsed_config.paragraph_pause_seconds, 1.0)
        self.assertEqual(parsed_config.synthesis_temperature, 0.65)
        self.assertEqual(parsed_config.chapter_pause_seconds, 2.0)

    def test_find_config_toml_path_explicit_argument(self):
        existing_toml_path = self.base_path / "direct_config.toml"
        existing_toml_path.write_text("voice = 'juno'", encoding="utf-8")

        found_path = find_config_toml_path(existing_toml_path)
        self.assertEqual(found_path, existing_toml_path.resolve())

        missing_path = find_config_toml_path(self.base_path / "missing.toml")
        self.assertIsNone(missing_path)

    def test_find_config_toml_path_via_environment_variable(self):
        env_toml_path = self.base_path / "env_config.toml"
        env_toml_path.write_text("voice = 'mira'", encoding="utf-8")

        original_env = os.environ.get("WOOFBOOK_CONFIG_FILE")
        try:
            os.environ["WOOFBOOK_CONFIG_FILE"] = str(env_toml_path)
            found_path = find_config_toml_path()
            self.assertEqual(found_path, env_toml_path.resolve())
        finally:
            if original_env is not None:
                os.environ["WOOFBOOK_CONFIG_FILE"] = original_env
            else:
                os.environ.pop("WOOFBOOK_CONFIG_FILE", None)

    def test_reload_configuration_updates_module_variables(self):
        temp_config_path = self.base_path / "reload_test.toml"
        temp_config_path.write_text(
            """
[model]
voice = "mira"
[audio]
format = "wav"
""",
            encoding="utf-8",
        )

        original_voice = config.DEFAULT_VOICE
        original_format = config.DEFAULT_OUTPUT_FORMAT

        try:
            config.reload_configuration(temp_config_path)
            self.assertEqual(config.DEFAULT_VOICE, "mira")
            self.assertEqual(config.DEFAULT_OUTPUT_FORMAT, "wav")
        finally:
            config.reload_configuration()
            self.assertEqual(config.DEFAULT_VOICE, original_voice)
            self.assertEqual(config.DEFAULT_OUTPUT_FORMAT, original_format)


if __name__ == "__main__":
    unittest.main()
