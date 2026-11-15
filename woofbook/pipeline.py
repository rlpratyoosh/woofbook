import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from .audio_exporter import AudioExporter
from .checkpoint_manager import CheckpointManager
from .config import (
    AUDIO_SAMPLE_RATE,
    DEFAULT_AUDIO_BITRATE,
    DEFAULT_AUDIO_OUTPUT_DIRECTORY,
    DEFAULT_CHAPTER_PAUSE_SECONDS,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_PARAGRAPH_PAUSE_SECONDS,
    DEFAULT_VOICE,
)
from .pdf_extractor import Chapter, PDFExtractor
from .tts_engine import TTSEngine


def sanitize_filename(text: str) -> str:
    cleaned_text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", cleaned_text)


slugify = sanitize_filename


class WoofbookPipeline:
    def __init__(
        self,
        pdf_path: str | Path,
        output_directory: Optional[str | Path] = None,
        voice: str = DEFAULT_VOICE,
        audio_format: str = DEFAULT_OUTPUT_FORMAT,
        model_weights_path: Optional[str | Path] = None,
        paragraph_pause_seconds: float = DEFAULT_PARAGRAPH_PAUSE_SECONDS,
        chapter_pause_seconds: float = DEFAULT_CHAPTER_PAUSE_SECONDS,
        audio_bitrate: str = DEFAULT_AUDIO_BITRATE,
        start_page: int = 1,
        end_page: Optional[int] = None,
        force_regeneration: bool = False,
        output_dir: Optional[str | Path] = None,
        weights_path: Optional[str | Path] = None,
        paragraph_pause: Optional[float] = None,
        chapter_pause: Optional[float] = None,
        bitrate: Optional[str] = None,
        force_fresh: Optional[bool] = None,
    ):
        resolved_output_directory = output_directory or output_dir
        resolved_weights_path = model_weights_path or weights_path
        if paragraph_pause is not None:
            paragraph_pause_seconds = paragraph_pause
        if chapter_pause is not None:
            chapter_pause_seconds = chapter_pause
        if bitrate is not None:
            audio_bitrate = bitrate
        if force_fresh is not None:
            force_regeneration = force_fresh

        self.pdf_path = Path(pdf_path).resolve()
        self.voice = voice
        self.audio_format = audio_format.lower().lstrip(".")
        self.paragraph_pause_seconds = paragraph_pause_seconds
        self.chapter_pause_seconds = chapter_pause_seconds
        self.audio_bitrate = audio_bitrate
        self.start_page = start_page
        self.end_page = end_page
        self.force_regeneration = force_regeneration

        self.pdf_extractor = PDFExtractor(self.pdf_path)
        self.book_metadata = self.pdf_extractor.get_metadata()

        book_title = self.book_metadata.get("title") or self.pdf_path.stem
        book_directory_slug = sanitize_filename(book_title)
        if resolved_output_directory:
            self.book_output_directory = Path(resolved_output_directory).resolve()
        else:
            self.book_output_directory = Path(DEFAULT_AUDIO_OUTPUT_DIRECTORY).resolve() / book_directory_slug

        self.book_output_directory.mkdir(parents=True, exist_ok=True)
        self.checkpoint_manager = CheckpointManager(self.book_output_directory)
        if self.force_regeneration:
            self.checkpoint_manager.clear_checkpoints()

        self.audio_exporter = AudioExporter(sample_rate=AUDIO_SAMPLE_RATE)
        self._tts_engine: Optional[TTSEngine] = None
        self._model_weights_path = resolved_weights_path

        self.extractor = self.pdf_extractor
        self.metadata = self.book_metadata
        self.book_output_dir = self.book_output_directory
        self.checkpoint = self.checkpoint_manager
        self.exporter = self.audio_exporter

    @property
    def tts_engine(self) -> TTSEngine:
        if self._tts_engine is None:
            engine_arguments = {"voice": self.voice}
            if self._model_weights_path:
                engine_arguments["model_weights_path"] = self._model_weights_path
            self._tts_engine = TTSEngine(**engine_arguments)
        return self._tts_engine

    @property
    def tts(self) -> TTSEngine:
        return self.tts_engine

    def list_chapters(self) -> List[Chapter]:
        return self.pdf_extractor.extract_chapters(
            start_page=self.start_page, end_page=self.end_page
        )

    def dry_run_export_text(
        self,
        destination_text_path: Optional[Path] = None,
        output_txt_path: Optional[Path] = None,
    ) -> Path:
        chapters = self.list_chapters()
        target_path = destination_text_path or output_txt_path
        if target_path is None:
            target_path = self.book_output_directory / f"{self.pdf_path.stem}_cleaned.txt"

        resolved_text_path = Path(target_path).resolve()
        with open(resolved_text_path, "w", encoding="utf-8") as text_file:
            text_file.write(f"Book Title : {self.book_metadata.get('title')}\n")
            text_file.write(f"Author     : {self.book_metadata.get('author')}\n")
            text_file.write(f"Source PDF : {self.pdf_path}\n")
            text_file.write(f"Total Pages: {self.book_metadata.get('pages')}\n")
            text_file.write("=" * 60 + "\n\n")

            for chapter in chapters:
                text_file.write(
                    f"### Chapter {chapter.index}: {chapter.title} (Pages {chapter.start_page}-{chapter.end_page}) ###\n\n"
                )
                for paragraph in chapter.paragraphs:
                    text_file.write(paragraph + "\n\n")

        return resolved_text_path

    def run(self, merge_master: bool = True) -> Dict[str, any]:
        pipeline_start_time = time.time()
        print("\n" + "=" * 65)
        print(f"📖 Starting Woofbook Generation: {self.book_metadata.get('title')}")
        print(f"👤 Author      : {self.book_metadata.get('author')}")
        print(f"🎙️  Voice       : {self.voice}")
        print(f"🎵 Format      : {self.audio_format.upper()} ({self.audio_bitrate})")
        print(f"📁 Output Dir  : {self.book_output_directory}")
        print("=" * 65)

        chapters = self.list_chapters()
        if not chapters:
            print("❌ No readable chapters or text found in the specified page range.")
            return {"status": "error", "error": "No text extracted"}

        total_word_count = sum(chapter.total_words for chapter in chapters)
        print(f"\n📊 Extracted {len(chapters)} chapter(s) ({total_word_count:,} words total).\n")

        completed_chapter_file_paths: List[Path] = []

        for chapter in chapters:
            formatted_chapter_index = f"{chapter.index:02d}"
            chapter_slug = sanitize_filename(chapter.title)
            chapter_filename = f"Chapter_{formatted_chapter_index}_{chapter_slug}.{self.audio_format}"
            chapter_audio_path = self.book_output_directory / chapter_filename

            if self.checkpoint_manager.is_chapter_completed(chapter.index):
                existing_file_path = self.checkpoint_manager.get_completed_chapter_file_path(chapter.index)
                if existing_file_path and existing_file_path.exists():
                    print(f"⏩ [Chapter {chapter.index}/{len(chapters)}] '{chapter.title}' already exists. Skipping.")
                    completed_chapter_file_paths.append(existing_file_path)
                    continue

            print("-" * 65)
            print(f"🎙️ Synthesizing Chapter {chapter.index}/{len(chapters)}: \"{chapter.title}\"")
            print(
                f"   Pages {chapter.start_page}-{chapter.end_page} | "
                f"{len(chapter.paragraphs)} paragraphs | {chapter.total_words:,} words"
            )

            chapter_start_time = time.time()

            def render_progress(
                current_paragraph_index: int,
                total_paragraph_count: int,
                paragraph_text: str,
            ):
                preview_snippet = (
                    (paragraph_text[:50] + "...")
                    if len(paragraph_text) > 50
                    else paragraph_text
                )
                cleaned_preview = preview_snippet.replace("\n", " ")
                completion_percentage = int((current_paragraph_index / total_paragraph_count) * 100)
                sys.stdout.write(
                    f"\r   [{completion_percentage:3d}%] Para {current_paragraph_index}/{total_paragraph_count}: \"{cleaned_preview}\"\033[K"
                )
                sys.stdout.flush()

            chapter_audio_samples = self.tts_engine.synthesize_paragraphs(
                chapter.paragraphs,
                pause_duration_seconds=self.paragraph_pause_seconds,
                progress_callback=render_progress,
            )
            sys.stdout.write("\n")

            chapter_metadata = {
                "title": f"Chapter {chapter.index}: {chapter.title}",
                "album": self.book_metadata.get("title", "Audiobook"),
                "artist": self.book_metadata.get("author", "Unknown"),
                "track": str(chapter.index),
            }
            exported_chapter_audio_path = self.audio_exporter.export(
                chapter_audio_samples,
                chapter_audio_path,
                audio_format=self.audio_format,
                bitrate=self.audio_bitrate,
                metadata=chapter_metadata,
            )
            chapter_duration_seconds = time.time() - chapter_start_time
            print(f"   ✅ Saved: {exported_chapter_audio_path.name} (took {chapter_duration_seconds:.1f}s)")

            self.checkpoint_manager.record_chapter_completion(
                chapter.index, exported_chapter_audio_path, chapter.title
            )
            completed_chapter_file_paths.append(exported_chapter_audio_path)

        master_audiobook_path = None
        if merge_master and len(completed_chapter_file_paths) > 1:
            print("\n" + "=" * 65)
            print("🔀 Merging chapters into single complete audiobook...")
            master_filename = f"{sanitize_filename(self.book_metadata.get('title'))}_complete.{self.audio_format}"
            master_destination_path = self.book_output_directory / master_filename

            audiobook_metadata = {
                "title": self.book_metadata.get("title", "Audiobook"),
                "album": self.book_metadata.get("title", "Audiobook"),
                "artist": self.book_metadata.get("author", "Unknown"),
            }

            master_audiobook_path = self.audio_exporter.merge_audio_files(
                input_audio_paths=completed_chapter_file_paths,
                output_path=master_destination_path,
                silence_between_files_seconds=self.chapter_pause_seconds,
                audio_format=self.audio_format,
                bitrate=self.audio_bitrate,
                metadata=audiobook_metadata,
            )
            print(f"✨ Master Audiobook Created: {master_audiobook_path}")

        total_elapsed_seconds = time.time() - pipeline_start_time
        print("\n" + "=" * 65)
        print("🎉 Finished!")
        print(f"⏱️ Total time elapsed : {total_elapsed_seconds / 60:.2f} minutes")
        print(f"📂 Output directory   : {self.book_output_directory}")
        print("=" * 65 + "\n")

        return {
            "status": "success",
            "chapters": completed_chapter_file_paths,
            "master_file": master_audiobook_path,
            "elapsed_seconds": total_elapsed_seconds,
        }


AudiobookPipeline = WoofbookPipeline
