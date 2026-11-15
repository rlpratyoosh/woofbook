import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


@dataclass
class WoofbookConfiguration:
    model_directory: str = "./"
    model_weights_path: str = "./woof_int8.npz"
    books_directory: Path = field(default_factory=lambda: Path("books").resolve())
    audio_output_directory: Path = field(default_factory=lambda: Path("output").resolve())
    sample_rate: int = 24000
    available_voices: Tuple[str, ...] = ("juno", "mira")
    voice: str = "juno"
    output_format: str = "mp3"
    audio_bitrate: str = "128k"
    paragraph_pause_seconds: float = 0.45
    chapter_pause_seconds: float = 2.0
    synthesis_temperature: float = 0.5
    end_of_speech_threshold: float = 0.9
    max_retries: int = 3


AudiobookConfiguration = WoofbookConfiguration


def find_config_toml_path(custom_config_path: Optional[str | Path] = None) -> Optional[Path]:
    if custom_config_path:
        explicit_path = Path(custom_config_path).expanduser().resolve()
        if explicit_path.exists():
            return explicit_path
        return None

    environment_config_path = os.environ.get("WOOFBOOK_CONFIG_FILE") or os.environ.get("AUDIOBOOK_CONFIG_FILE")
    if environment_config_path:
        env_path = Path(environment_config_path).expanduser().resolve()
        if env_path.exists():
            return env_path

    current_working_directory_config = Path.cwd() / "config.toml"
    if current_working_directory_config.exists():
        return current_working_directory_config.resolve()

    project_root_directory = Path(__file__).resolve().parent.parent
    project_root_config = project_root_directory / "config.toml"
    if project_root_config.exists():
        return project_root_config.resolve()

    return None


def _resolve_relative_path(path_string: str, base_directory: Path) -> Path:
    target_path = Path(path_string).expanduser()
    if target_path.is_absolute():
        return target_path.resolve()
    return (base_directory / target_path).resolve()


def parse_config_toml(config_path: Optional[str | Path] = None) -> WoofbookConfiguration:
    default_configuration = WoofbookConfiguration()
    resolved_config_path = find_config_toml_path(config_path)

    combined_toml_entries: Dict[str, Any] = {}
    base_directory = Path.cwd()

    if resolved_config_path and resolved_config_path.exists():
        base_directory = resolved_config_path.parent
        with open(resolved_config_path, "rb") as toml_file:
            raw_toml_data = tomllib.load(toml_file)

        for section_name in ("model", "audio", "paths", "synthesis"):
            section_data = raw_toml_data.get(section_name)
            if isinstance(section_data, dict):
                combined_toml_entries.update(section_data)

        for top_level_key, top_level_value in raw_toml_data.items():
            if not isinstance(top_level_value, dict):
                combined_toml_entries[top_level_key] = top_level_value

    def extract_value(*candidate_keys: str, default: Any) -> Any:
        for candidate_key in candidate_keys:
            if candidate_key in combined_toml_entries:
                return combined_toml_entries[candidate_key]
        return default

    model_dir_raw = extract_value(
        "model_directory", "model_dir", default=default_configuration.model_directory
    )
    model_directory_env = os.environ.get("WOOF_MODEL_DIR")
    if model_directory_env:
        resolved_model_directory = str(Path(model_directory_env).expanduser().resolve())
    else:
        resolved_model_directory = str(_resolve_relative_path(str(model_dir_raw), base_directory))

    weights_raw = extract_value(
        "weights_path", "model_weights_path", default=default_configuration.model_weights_path
    )
    weights_path_env = os.environ.get("WOOF_WEIGHTS_PATH")
    if weights_path_env:
        resolved_weights_path = str(Path(weights_path_env).expanduser().resolve())
    else:
        resolved_weights_path = str(_resolve_relative_path(str(weights_raw), base_directory))

    books_dir_raw = extract_value(
        "books_directory", "books_dir", default=str(default_configuration.books_directory)
    )
    resolved_books_directory = _resolve_relative_path(str(books_dir_raw), base_directory)

    audio_dir_raw = extract_value(
        "audio_output_directory", "output_dir", "audio_dir", default=str(default_configuration.audio_output_directory)
    )
    resolved_audio_output_directory = _resolve_relative_path(str(audio_dir_raw), base_directory)

    configured_sample_rate = int(
        extract_value("sample_rate", default=default_configuration.sample_rate)
    )
    configured_voice = str(
        extract_value("voice", default=default_configuration.voice)
    ).lower()
    configured_output_format = str(
        extract_value("output_format", "format", default=default_configuration.output_format)
    ).lower().lstrip(".")
    configured_bitrate = str(
        extract_value("audio_bitrate", "bitrate", default=default_configuration.audio_bitrate)
    )
    configured_paragraph_pause = float(
        extract_value(
            "paragraph_pause_seconds", "paragraph_pause", default=default_configuration.paragraph_pause_seconds
        )
    )
    configured_chapter_pause = float(
        extract_value(
            "chapter_pause_seconds", "chapter_pause", default=default_configuration.chapter_pause_seconds
        )
    )
    configured_temperature = float(
        extract_value(
            "synthesis_temperature", "temperature", "temp", default=default_configuration.synthesis_temperature
        )
    )
    configured_eos = float(
        extract_value(
            "end_of_speech_threshold", "eos", default=default_configuration.end_of_speech_threshold
        )
    )
    configured_max_retries = int(
        extract_value(
            "max_retries", "retries", default=default_configuration.max_retries
        )
    )

    return WoofbookConfiguration(
        model_directory=resolved_model_directory,
        model_weights_path=resolved_weights_path,
        books_directory=resolved_books_directory,
        audio_output_directory=resolved_audio_output_directory,
        sample_rate=configured_sample_rate,
        available_voices=default_configuration.available_voices,
        voice=configured_voice,
        output_format=configured_output_format,
        audio_bitrate=configured_bitrate,
        paragraph_pause_seconds=configured_paragraph_pause,
        chapter_pause_seconds=configured_chapter_pause,
        synthesis_temperature=configured_temperature,
        end_of_speech_threshold=configured_eos,
        max_retries=configured_max_retries,
    )
