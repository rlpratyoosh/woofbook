import json
import time
from pathlib import Path
from typing import Optional


class CheckpointManager:
    def __init__(self, book_output_directory: Path):
        self.book_output_directory = Path(book_output_directory).resolve()
        self.book_output_directory.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file_path = self.book_output_directory / ".checkpoint.json"
        self.checkpoint_data = self._load_checkpoint_data()

    def _load_checkpoint_data(self) -> dict:
        if self.checkpoint_file_path.exists():
            try:
                with open(self.checkpoint_file_path, "r", encoding="utf-8") as checkpoint_file:
                    return json.load(checkpoint_file)
            except Exception:
                return {"completed_chapters": {}}
        return {"completed_chapters": {}}

    def _save_checkpoint_data(self) -> None:
        with open(self.checkpoint_file_path, "w", encoding="utf-8") as checkpoint_file:
            json.dump(self.checkpoint_data, checkpoint_file, indent=2)

    def is_chapter_completed(self, chapter_index: int) -> bool:
        chapter_key = str(chapter_index)
        completed_chapters = self.checkpoint_data.get("completed_chapters", {})
        if chapter_key in completed_chapters:
            audio_file_path = Path(completed_chapters[chapter_key]["file_path"])
            if audio_file_path.exists() and audio_file_path.stat().st_size > 0:
                return True
        return False

    def get_completed_chapter_file_path(self, chapter_index: int) -> Optional[Path]:
        chapter_key = str(chapter_index)
        if self.is_chapter_completed(chapter_index):
            return Path(self.checkpoint_data["completed_chapters"][chapter_key]["file_path"])
        return None

    def record_chapter_completion(
        self,
        chapter_index: int,
        audio_file_path: Path,
        chapter_title: str,
    ) -> None:
        if "completed_chapters" not in self.checkpoint_data:
            self.checkpoint_data["completed_chapters"] = {}

        self.checkpoint_data["completed_chapters"][str(chapter_index)] = {
            "title": chapter_title,
            "file_path": str(audio_file_path.resolve()),
            "timestamp": time.time(),
        }
        self._save_checkpoint_data()

    def clear_checkpoints(self) -> None:
        if self.checkpoint_file_path.exists():
            self.checkpoint_file_path.unlink()
        self.checkpoint_data = {"completed_chapters": {}}

    get_completed_file = get_completed_chapter_file_path
    record_chapter = record_chapter_completion
    clear = clear_checkpoints
