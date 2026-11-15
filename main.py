#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

import audiobook.config as config
from audiobook.config import reload_configuration
from audiobook.pipeline import AudiobookPipeline


def main() -> None:
    preliminary_parser = argparse.ArgumentParser(add_help=False)
    preliminary_parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
    )
    preliminary_arguments, _ = preliminary_parser.parse_known_args()
    if preliminary_arguments.config:
        reload_configuration(preliminary_arguments.config)

    argument_parser = argparse.ArgumentParser(
        description="Convert PDF books to full audiobooks."
    )
    argument_parser.add_argument(
        "pdf",
        nargs="?",
        type=str,
        help="Path to the .pdf book file to convert.",
    )
    argument_parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help="Path to custom config.toml configuration file (default: config.toml in project root).",
    )
    argument_parser.add_argument(
        "-v",
        "--voice",
        choices=config.AVAILABLE_VOICES,
        default=config.DEFAULT_VOICE,
        help=f"Voice to use for synthesis (default: {config.DEFAULT_VOICE}). Choices: {config.AVAILABLE_VOICES}",
    )
    argument_parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save the audiobook (default: output/<book_title>/).",
    )
    argument_parser.add_argument(
        "-f",
        "--format",
        choices=["mp3", "wav", "m4b"],
        default=config.DEFAULT_OUTPUT_FORMAT,
        help=f"Audio format for output files (default: {config.DEFAULT_OUTPUT_FORMAT}).",
    )
    argument_parser.add_argument(
        "-b",
        "--bitrate",
        type=str,
        default=config.DEFAULT_AUDIO_BITRATE,
        help=f"Audio bitrate for mp3/m4b output (default: {config.DEFAULT_AUDIO_BITRATE}).",
    )
    argument_parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="First page of the PDF to convert (1-indexed, default: 1).",
    )
    argument_parser.add_argument(
        "--end-page",
        type=int,
        default=None,
        help="Last page of the PDF to convert (default: until the end of the PDF).",
    )
    argument_parser.add_argument(
        "--paragraph-pause",
        type=float,
        default=config.DEFAULT_PARAGRAPH_PAUSE_SECONDS,
        help=f"Silence duration in seconds between paragraphs (default: {config.DEFAULT_PARAGRAPH_PAUSE_SECONDS}s).",
    )
    argument_parser.add_argument(
        "--chapter-pause",
        type=float,
        default=config.DEFAULT_CHAPTER_PAUSE_SECONDS,
        help=f"Silence duration in seconds between chapters (default: {config.DEFAULT_CHAPTER_PAUSE_SECONDS}s).",
    )
    argument_parser.add_argument(
        "--weights",
        type=str,
        default=None,
        help="Custom path to woof_int8.npz model weights (defaults to woof_int8.npz).",
    )
    argument_parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Do not merge chapter files into a single master audiobook file.",
    )
    argument_parser.add_argument(
        "--list-chapters",
        action="store_true",
        help="Inspect and list detected chapters and word counts without synthesizing audio.",
    )
    argument_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and clean text from the PDF to a preview .txt file without synthesizing audio.",
    )
    argument_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-generation of all chapters, ignoring existing checkpoints.",
    )

    parsed_arguments = argument_parser.parse_args()

    if not parsed_arguments.pdf:
        books_directory = Path(config.DEFAULT_BOOKS_DIRECTORY)
        discovered_pdf_files = list(books_directory.glob("*.pdf")) if books_directory.exists() else []
        if discovered_pdf_files:
            print("No PDF path specified. Found available PDF(s) in books/:")
            for display_index, discovered_file_path in enumerate(discovered_pdf_files, start=1):
                print(f"  [{display_index}] {discovered_file_path}")
            print("\nUsage example: python main.py books/<filename>.pdf")
            sys.exit(0)
        else:
            argument_parser.print_help()
            sys.exit(1)

    input_pdf_path = Path(parsed_arguments.pdf)
    if not input_pdf_path.exists():
        print(f"Error: File not found: {input_pdf_path}", file=sys.stderr)
        sys.exit(1)

    try:
        audiobook_pipeline = AudiobookPipeline(
            pdf_path=input_pdf_path,
            output_directory=parsed_arguments.output_dir,
            voice=parsed_arguments.voice,
            audio_format=parsed_arguments.format,
            model_weights_path=parsed_arguments.weights,
            paragraph_pause_seconds=parsed_arguments.paragraph_pause,
            chapter_pause_seconds=parsed_arguments.chapter_pause,
            audio_bitrate=parsed_arguments.bitrate,
            start_page=parsed_arguments.start_page,
            end_page=parsed_arguments.end_page,
            force_regeneration=parsed_arguments.force,
        )

        if parsed_arguments.list_chapters:
            extracted_chapters = audiobook_pipeline.list_chapters()
            print(f"\n📖 Detected {len(extracted_chapters)} chapter(s) in '{input_pdf_path.name}':")
            print("-" * 65)
            for chapter in extracted_chapters:
                print(
                    f"Chapter {chapter.index:02d}: \"{chapter.title}\" | "
                    f"Pages {chapter.start_page}-{chapter.end_page} | "
                    f"{len(chapter.paragraphs)} paragraphs | {chapter.total_words:,} words"
                )
            print("-" * 65)
            return

        if parsed_arguments.dry_run:
            exported_text_path = audiobook_pipeline.dry_run_export_text()
            print(f"\n✅ Dry run completed! Cleaned text exported to:\n   {exported_text_path}")
            return

        audiobook_pipeline.run(merge_master=not parsed_arguments.no_merge)

    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user. Completed chapters were safely saved to checkpoint.")
        sys.exit(130)
    except Exception as runtime_error:
        print(f"\n❌ Error: {runtime_error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
