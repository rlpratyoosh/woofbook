# 🐶 Woofbook

A lightweight Python tool that converts `.pdf` books into chapterized audiobooks using the [Underdog-Woof](https://huggingface.co/ConwayResearch/Underdog-Woof) text-to-speech model by Conway Research.

> [!NOTE]
> **About This Project**: This project was created with the help of AI as a personal fun project. Contributions, feedback, and pull requests are warmly welcomed!

---

## ✨ Features

- **Automatic PDF Text Cleaning**:
  - Automatically joins hyphenated words split across lines (`some-` + `thing` $\rightarrow$ `something`).
  - Cleans headers, footers, standalone page numbers, and typographic ligatures (`ﬁ` $\rightarrow$ `fi`, `—` $\rightarrow$ `--`).
  - Preserves paragraphs and dialogue flow.
- **Smart Chapter Detection**:
  - Automatically discovers chapters (`Chapter 1`, `CHAPTER IV`, `Prologue`, etc.).
  - Generates individual audio tracks for each chapter (`Chapter_01_....mp3`, `Chapter_02_....mp3`).
  - Merges all chapters into a seamless master audiobook (`<Book_Title>_complete.mp3`).
- **Resumption & Checkpointing**:
  - Automatically caches completed chapters in `.checkpoint.json`. If cancelled or interrupted, re-running resumes from the unfinished chapter without re-generating previous audio.
- **Configurable Pacing & Silence**:
  - Natural silence intervals between paragraphs (default: `0.45s`) and chapters (default: `2.0s`).
- **Multiple Voices & Formats**:
  - Built-in voices: `juno` (default) and `mira`.
  - Audio formats: `mp3` (default, 128 kbps), `wav` (uncompressed 24 kHz), and `m4b`.
- **Zero-Code Configuration (`config.toml`)**:
  - Customize all parameters via `config.toml` at the project root without modifying Python code.

---

## 📋 Prerequisites

Before running the generator, ensure system dependencies are installed:

### 1. System Dependencies

- **Python**: 3.11 or higher
- **Poppler Utils** (for PDF text and metadata extraction):
  ```bash
  # Ubuntu / Debian
  sudo apt install poppler-utils

  # macOS (Homebrew)
  brew install poppler

  # Arch Linux
  sudo pacman -S poppler
  ```
- **FFmpeg** (for MP3/M4B encoding and audio merging):
  ```bash
  # Ubuntu / Debian
  sudo apt install ffmpeg

  # macOS (Homebrew)
  brew install ffmpeg

  # Arch Linux
  sudo pacman -S ffmpeg
  ```

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/rlpratyoosh/woofbook.git
cd woofbook
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### 3. Generate an Audiobook

The quantized model weights (`woof_int8.npz`, ~39 MB) are already bundled directly in the repository, so no extra downloads are required. Place your PDF file into `books/` (or pass any path directly):

```bash
# Using the launcher script
./run.sh books/sample_book.pdf

# Or using Python directly
python3 main.py books/sample_book.pdf
```

Output files will be saved in `output/<book_title>/`.

---

## ⚙️ Configuration (`config.toml`)

You can customize default behavior in `config.toml` at the project root:

```toml
[model]
model_directory = "./"
weights_path = "./woof_int8.npz"
voice = "juno"
temperature = 0.5
end_of_speech_threshold = 0.9
max_retries = 3

[audio]
format = "mp3"
bitrate = "128k"
sample_rate = 24000
paragraph_pause_seconds = 0.45
chapter_pause_seconds = 2.0

[paths]
books_directory = "books"
audio_output_directory = "output"
```

You can also specify a custom configuration file at runtime:
```bash
./run.sh books/my_book.pdf --config custom_config.toml
```

---

## 🛠️ CLI Options & Usage Examples

### Inspect Chapters Before Synthesizing
Preview detected chapters, word counts, and page ranges without generating audio:
```bash
./run.sh books/my_book.pdf --list-chapters
```

### Dry Run (Review Extracted Text)
Extract and clean text from the PDF into a preview `.txt` file without audio synthesis:
```bash
./run.sh books/my_book.pdf --dry-run
```

### Choose Voice
Switch between `juno` (default) and `mira`:
```bash
./run.sh books/my_book.pdf --voice mira
```

### Convert Specific Page Ranges
Test a specific range or skip introductory front matter:
```bash
./run.sh books/my_book.pdf --start-page 10 --end-page 25
```

### Choose Audio Format & Bitrate
```bash
# Uncompressed WAV output
./run.sh books/my_book.pdf --format wav

# High quality MP3
./run.sh books/my_book.pdf --format mp3 --bitrate 192k

# M4B Audiobook format
./run.sh books/my_book.pdf --format m4b
```

### Custom Pauses
Customize silence duration between paragraphs and chapters:
```bash
./run.sh books/my_book.pdf --paragraph-pause 0.5 --chapter-pause 2.5
```

### Force Regeneration
Rebuild all chapters from scratch, ignoring existing checkpoints:
```bash
./run.sh books/my_book.pdf --force
```

### Disable Complete File Merging
Keep individual chapter files only:
```bash
./run.sh books/my_book.pdf --no-merge
```

---

## 🧪 Running Tests

The test suite includes 47 unit and integration tests covering all modules:

```bash
# Run using the test script
./run_tests.sh

# Or run directly with Python
python3 run_tests.py
```

---

## 📁 Directory Structure

```
woofbook/
├── books/                        # Place input PDF files here
│   └── sample_book.pdf
├── output/                       # Output directory for generated audiobooks
│   └── <book_title>/
│       ├── Chapter_01_....mp3
│       ├── Chapter_02_....mp3
│       ├── <book_title>_complete.mp3
│       └── .checkpoint.json
├── woofbook/                     # Core library
│   ├── __init__.py
│   ├── config.py                 # Configuration loader
│   ├── config_parser.py          # TOML configuration parser
│   ├── pdf_extractor.py          # PDF text extraction & chapter detection
│   ├── tts_engine.py             # Underdog-Woof model wrapper
│   ├── audio_exporter.py         # FFmpeg / Wave audio encoding & merging
│   ├── checkpoint_manager.py     # Checkpoint tracker
│   └── pipeline.py               # End-to-end pipeline coordinator
├── tests/                        # Test suite (47 unit & integration tests)
├── config.toml                   # Root configuration file
├── main.py                       # CLI application
├── run.sh                        # Shell launcher script
├── run_tests.sh                  # Test runner script
├── requirements.txt              # Python dependencies
├── woof_int8.npz                 # Bundled Underdog-Woof quantized weights (~39 MB)
├── .gitignore                    # Git ignore file
└── README.md
```

---

## 🤝 Contributing & Community

This project was created with the help of AI as a personal fun project. Contributions, feature suggestions, bug reports, and pull requests are warmly welcomed!

- 🐛 Bug fixes and edge case reporting (e.g. unique PDF formatting)
- 💡 Ideas for improving chapter detection heuristics
- 🚀 Support for additional input formats (e.g. EPUB, MOBI)
- 📝 Documentation and example improvements

Feel free to open an issue or submit a pull request!

---

## 🙏 Acknowledgements

- [Underdog-Woof](https://huggingface.co/ConwayResearch/Underdog-Woof) by Conway Research for the compact, fast CPU-based text-to-speech model.
- [Poppler](https://poppler.freedesktop.org/) for robust PDF text extraction tools.
- [FFmpeg](https://ffmpeg.org/) for audio processing and conversion.
