import sys
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .config import (
    AUDIO_SAMPLE_RATE,
    AVAILABLE_VOICES,
    DEFAULT_END_OF_SPEECH_THRESHOLD,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL_DIRECTORY,
    DEFAULT_MODEL_WEIGHTS_PATH,
    DEFAULT_PARAGRAPH_PAUSE_SECONDS,
    DEFAULT_SYNTHESIS_TEMPERATURE,
    DEFAULT_VOICE,
)


class TTSEngine:
    def __init__(
        self,
        model_weights_path: str | Path = DEFAULT_MODEL_WEIGHTS_PATH,
        model_directory: str | Path = DEFAULT_MODEL_DIRECTORY,
        voice: str = DEFAULT_VOICE,
        temperature: float = DEFAULT_SYNTHESIS_TEMPERATURE,
        end_of_speech_threshold: float = DEFAULT_END_OF_SPEECH_THRESHOLD,
        max_retries: int = DEFAULT_MAX_RETRIES,
        weights_path: Optional[str | Path] = None,
        model_dir: Optional[str | Path] = None,
        temp: Optional[float] = None,
        eos: Optional[float] = None,
        retries: Optional[int] = None,
    ):
        self.model_weights_path = Path(weights_path or model_weights_path).expanduser().resolve()
        self.model_directory = Path(model_dir or model_directory).expanduser().resolve()
        self.voice = voice.lower()
        self.temperature = temp if temp is not None else temperature
        self.end_of_speech_threshold = eos if eos is not None else end_of_speech_threshold
        self.max_retries = retries if retries is not None else max_retries
        self.sample_rate = AUDIO_SAMPLE_RATE

        self.weights_path = self.model_weights_path
        self.model_dir = self.model_directory
        self.temp = self.temperature
        self.eos = self.end_of_speech_threshold
        self.retries = self.max_retries
        self.sr = self.sample_rate

        if self.voice not in AVAILABLE_VOICES:
            raise ValueError(
                f"Unknown voice '{self.voice}'. Choose from: {AVAILABLE_VOICES}"
            )

        if not self.model_weights_path.exists():
            raise FileNotFoundError(
                f"Weights file not found at: {self.model_weights_path}. "
                f"Ensure underdog-woof is present or set --weights."
            )

        if str(self.model_directory) not in sys.path:
            sys.path.insert(0, str(self.model_directory))

        try:
            from underdog_woof import Woof
        except ImportError as import_error:
            raise ImportError(
                f"Failed to import underdog_woof from {self.model_directory}: {import_error}"
            ) from import_error

        self.woof_model = Woof(
            weights=str(self.model_weights_path),
            voice=self.voice,
            temp=self.temperature,
            eos=self.end_of_speech_threshold,
            retries=self.max_retries,
            normalize=True,
        )
        self.woof = self.woof_model

    def generate_silence(self, duration_seconds: float) -> np.ndarray:
        frame_count = int(round(self.sample_rate * max(0.0, duration_seconds)))
        return np.zeros(frame_count, dtype=np.float32)

    def silence(self, seconds: float) -> np.ndarray:
        return self.generate_silence(seconds)

    def synthesize(
        self,
        text: str,
        random_seed: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> np.ndarray:
        cleaned_text = text.strip()
        if not cleaned_text:
            return np.zeros(0, dtype=np.float32)

        effective_seed = random_seed if random_seed is not None else seed
        return self.woof_model(cleaned_text, seed=effective_seed)

    def synthesize_paragraphs(
        self,
        paragraphs: list[str],
        pause_duration_seconds: float = DEFAULT_PARAGRAPH_PAUSE_SECONDS,
        pause_seconds: Optional[float] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> np.ndarray:
        effective_pause = pause_seconds if pause_seconds is not None else pause_duration_seconds
        synthesized_audio_segments = []
        silence_segment = self.generate_silence(effective_pause)
        total_paragraphs = len(paragraphs)

        for paragraph_index, paragraph_text in enumerate(paragraphs, start=1):
            cleaned_paragraph = paragraph_text.strip()
            if not cleaned_paragraph:
                continue

            if progress_callback:
                progress_callback(paragraph_index, total_paragraphs, cleaned_paragraph)

            paragraph_audio = self.synthesize(cleaned_paragraph)
            if len(paragraph_audio) > 0:
                synthesized_audio_segments.append(paragraph_audio)
                if paragraph_index < total_paragraphs and len(silence_segment) > 0:
                    synthesized_audio_segments.append(silence_segment)

        if not synthesized_audio_segments:
            return np.zeros(0, dtype=np.float32)

        return np.concatenate(synthesized_audio_segments).astype(np.float32)
