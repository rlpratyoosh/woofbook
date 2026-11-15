import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from .config import AUDIO_SAMPLE_RATE, DEFAULT_AUDIO_BITRATE

PCM_16BIT_MAX_AMPLITUDE = 32767.0
PCM_16BIT_BYTES_PER_SAMPLE = 2
MONO_CHANNEL_COUNT = 1


class AudioExporter:
    def __init__(self, sample_rate: int = AUDIO_SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.ffmpeg_executable_path = shutil.which("ffmpeg")

    def convert_float_to_pcm16(self, audio_samples: np.ndarray) -> np.ndarray:
        clipped_samples = np.clip(audio_samples, -1.0, 1.0)
        return (clipped_samples * PCM_16BIT_MAX_AMPLITUDE).round().astype("<i2")

    def save_wav(self, destination_path: str | Path, audio_samples: np.ndarray) -> Path:
        resolved_output_path = Path(destination_path).resolve()
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

        pcm_samples = self.convert_float_to_pcm16(audio_samples)
        with wave.open(str(resolved_output_path), "wb") as wav_file:
            wav_file.setnchannels(MONO_CHANNEL_COUNT)
            wav_file.setsampwidth(PCM_16BIT_BYTES_PER_SAMPLE)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_samples.tobytes())

        return resolved_output_path

    def export(
        self,
        audio_samples: np.ndarray,
        output_path: str | Path,
        audio_format: str = "mp3",
        bitrate: str = DEFAULT_AUDIO_BITRATE,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Path:
        resolved_output_path = Path(output_path).resolve()
        normalized_audio_format = audio_format.lower().lstrip(".")

        if normalized_audio_format == "wav" or not self.ffmpeg_executable_path:
            if normalized_audio_format != "wav" and not self.ffmpeg_executable_path:
                resolved_output_path = resolved_output_path.with_suffix(".wav")
            return self.save_wav(resolved_output_path, audio_samples)

        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        pcm_samples = self.convert_float_to_pcm16(audio_samples)

        ffmpeg_command = [
            self.ffmpeg_executable_path,
            "-y",
            "-f",
            "s16le",
            "-ar",
            str(self.sample_rate),
            "-ac",
            str(MONO_CHANNEL_COUNT),
            "-i",
            "pipe:0",
        ]

        if normalized_audio_format == "mp3":
            ffmpeg_command.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
        elif normalized_audio_format in ("m4b", "aac", "m4a"):
            ffmpeg_command.extend(["-c:a", "aac", "-b:a", bitrate])
        else:
            ffmpeg_command.extend(["-c:a", "pcm_s16le"])

        if metadata:
            for metadata_key, metadata_value in metadata.items():
                if metadata_value:
                    ffmpeg_command.extend(["-metadata", f"{metadata_key}={metadata_value}"])

        ffmpeg_command.append(str(resolved_output_path))

        subprocess.run(
            ffmpeg_command,
            input=pcm_samples.tobytes(),
            capture_output=True,
            check=True,
        )

        return resolved_output_path

    def merge_audio_files(
        self,
        input_audio_paths: List[Path],
        output_path: Path,
        silence_between_files_seconds: float = 0.0,
        audio_format: str = "mp3",
        bitrate: str = DEFAULT_AUDIO_BITRATE,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Path:
        resolved_output_path = Path(output_path).resolve()
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

        if not input_audio_paths:
            raise ValueError("No input files provided to merge.")

        if len(input_audio_paths) == 1 and silence_between_files_seconds <= 0:
            shutil.copy2(input_audio_paths[0], resolved_output_path)
            return resolved_output_path

        if not self.ffmpeg_executable_path:
            audio_segments = []
            silence_sample_count = int(round(self.sample_rate * silence_between_files_seconds))
            silence_pcm_samples = (
                np.zeros(silence_sample_count, dtype="<i2")
                if silence_between_files_seconds > 0
                else None
            )

            for file_index, audio_file_path in enumerate(input_audio_paths):
                with wave.open(str(audio_file_path), "rb") as wav_file:
                    audio_bytes = wav_file.readframes(wav_file.getnframes())
                    audio_segments.append(np.frombuffer(audio_bytes, dtype="<i2"))
                if silence_pcm_samples is not None and file_index < len(input_audio_paths) - 1:
                    audio_segments.append(silence_pcm_samples)

            concatenated_pcm_samples = np.concatenate(audio_segments)
            fallback_wav_path = resolved_output_path.with_suffix(".wav")
            with wave.open(str(fallback_wav_path), "wb") as wav_file:
                wav_file.setnchannels(MONO_CHANNEL_COUNT)
                wav_file.setsampwidth(PCM_16BIT_BYTES_PER_SAMPLE)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(concatenated_pcm_samples.tobytes())
            return fallback_wav_path

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_directory_path = Path(temporary_directory)
            concat_manifest_path = temporary_directory_path / "inputs.txt"

            silence_audio_path = None
            if silence_between_files_seconds > 0:
                silence_audio_path = temporary_directory_path / "silence.wav"
                silence_samples = np.zeros(
                    int(round(self.sample_rate * silence_between_files_seconds)),
                    dtype=np.float32,
                )
                self.save_wav(silence_audio_path, silence_samples)

            with open(concat_manifest_path, "w", encoding="utf-8") as manifest_file:
                for file_index, audio_file_path in enumerate(input_audio_paths):
                    manifest_file.write(f"file '{audio_file_path.resolve()}'\n")
                    if silence_audio_path and file_index < len(input_audio_paths) - 1:
                        manifest_file.write(f"file '{silence_audio_path.resolve()}'\n")

            ffmpeg_command = [
                self.ffmpeg_executable_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_manifest_path),
            ]

            normalized_audio_format = audio_format.lower().lstrip(".")
            if normalized_audio_format == "mp3":
                ffmpeg_command.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
            elif normalized_audio_format in ("m4b", "aac", "m4a"):
                ffmpeg_command.extend(["-c:a", "aac", "-b:a", bitrate])
            else:
                ffmpeg_command.extend(["-c:a", "copy"])

            if metadata:
                for metadata_key, metadata_value in metadata.items():
                    if metadata_value:
                        ffmpeg_command.extend(["-metadata", f"{metadata_key}={metadata_value}"])

            ffmpeg_command.append(str(resolved_output_path))
            subprocess.run(ffmpeg_command, capture_output=True, check=True)

        return resolved_output_path
