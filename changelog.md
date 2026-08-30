# Changelog

## Fixes for Manual/Raw JSON Input

### Core Functionality
- **Raw Segment Repair**: Implemented automatic detection and repair of segments that lack timestamp information (e.g. manually crafted JSON with just reference tags). The system now recalculates start/end times using the transcript alignment logic.
- **Duration Constraint Hardening**: The timestamp alignment logic now strictly enforces the user-defined `min_duration`, effectively extending segments that the AI might have outputted as too short.

## GGUF Support and Link Fixes

### What's New
- **GGUF Support**: added GGUF support for local LLMs.
- **Public Link**: adjusted public link directories.

## Video Quality, Subtitles, and Processing Improvements

### What's New

- **LLM prompt improvements**: prompt updates so the language model better understands content context.
- **Face detection improvements**: better identification of faces when several people are speaking at the same time.
- **Video Quality Selection**: you can now choose download quality (Best, 1080p, 720p, 480p) from the WebUI or CLI, to balance speed and storage use.
- **YouTube Subtitle Control**: added an option to skip downloading official YouTube subtitles, so a new Whisper transcription can be forced if desired.
- **VTT Support**: the transcription script now supports `.vtt` subtitle files for alignment, for better compatibility.
- **JSON subtitle translation with word-by-word highlight**: added translation of JSON subtitles, enabling word-by-word highlight and sync in another language during playback.

### Improvements and Optimizations

- **More robust yt-dlp**: fixed videos being saved as “Unknown_Video” and showing incorrect progress. Also added more accurate progress logs and improved subtitle download support.
- **YouTube Subtitle Optimization**: when YouTube subtitles are available, the system now downloads them automatically and uses them only for alignment, skipping the heavy, slow transcription step. This significantly speeds up processing of videos that already have captions.


## Active Speaker & Face Controls

### Advanced Face and Active Speaker Controls
- **Face Filters**: Granular control to ignore small faces, set a confidence threshold to reduce false positives, and a "Dead Zone" to stabilize the camera.
- **Experimental: Active Speaker**: New experimental mode that tries to focus on the person speaking (open-mouth and motion detection) instead of always splitting the screen.
- **Subtitles**: Option to strip punctuation automatically.

## JSON Subtitle Editor

### Features
- **Subtitle Editor**: Added a simple subtitle editor, within Gradio's limits, to fix spelling errors from WhisperX.

### Fixes
- **General**: Some Colab fixes and improvements to viral segment generation.

## Gradio WebUI & UV Installation

### New Web Interface (Gradio)
- **OpusClip Inspired**: New Gradio UI inspired by the OpusClip design, with a modern, intuitive user experience.
- **UI Features**: Full adjustments so every tool feature is accessible and working through the new interface.

### Installation and Infrastructure
- **UV Installation**: Created a `.bat` script for optimized dependency install via `uv`, speeding up setup.
- **General Fixes**: Fixes across components that were broken or unstable, improving stability when running via the UI.

## WebUI 2.0 & Enhanced Configuration

### WebUI Overhaul
- **Dark & Modern UI**: Interface fully redesigned with a dark theme and responsive grid layout (Opus.pro style) for the video gallery.
- **Dynamic Configuration**: Interface components now react dynamically to the AI Backend choice, automatically updating the available model list and the suggested chunk size.
- **Improved Controls**: Granular control over `Face Detect Interval`, `Skip Prompts`, and `Chunk Size` directly in the web interface.
- **Refactoring**: WebUI code refactored and modularized (`library.py` split from `app.py`) for easier maintenance.

### Core & CLI
- **Arguments Expansion**: `main_improved.py` now accepts command-line arguments for `--chunk-size` and `--ai-model-name`, allowing a full override of the configuration.
- **Script Update**: `create_viral_segments.py` updated to respect CLI parameters, prioritizing them over the config file.

## Fix 2 faces

### Face Detection and Layout Improvements
- **Visual Consistency (2 Faces)**: Implemented logic to "lock" face identities in the top and bottom positions, preventing participants from swapping places during the video.
- **Smart Fallback Logic**: If a face is not detected in the current frame, the system now tries to recover the position from the previous frame, the next frame, or the last known valid coordinate.
- **Customizable Detection Interval**: Added a setting so the user can choose how often face scanning runs, to optimize render time.

### Subtitle Fixes
- **Overlap Fix**: Fixed a bug where subtitles overlapped during fast speech.
- **Centering Refinement (2 Faces)**: Extra position-calculation tweaks so the subtitle stays perfectly centered in split-screen mode.

## Previous Updates

### Refactoring and Code Improvements
- **Main Script Refactor**: Created and improved `main_improved.py` to better structure and maintain the processing pipeline.
- **Code Standardization (English)**: Fully translated variable names, functions, and internal comments to English for international open-source collaboration, while keeping output logs with i18n support (`en_US`/`pt_BR`).
- **Directory Adjustments**: Reorganized folder structure and output paths for clearer generated files.

### Configuration and AI
- **Multi-LLM Integration**: Added support for **g4f** (GPT-4 Free) and **Google Gemini**.
- **API Config**: Centralized keys and model selection in the new `api_config.json` file, so the AI provider can be switched without changing code.
- **Prompt Management**: Created `prompt.txt` for easy system-prompt editing.

### Subtitles and Transcription (Whisper)
- **Whisper Fixes**: Robust handling of `unpickling` errors, DLL conflicts (`libprotobuf`, `torchaudio`), and GPU detection.
- **Flow Optimization (Slicing)**: The original video is transcribed only once. Cuts reuse the original JSON, eliminating re-transcription and speeding up the process.
- **Subtitle Positioning**: Fixed alignment logic for centering in "2-face" mode.

### Video Processing and Face Detection
- **New Engine: InsightFace**: Added the `InsightFace` library as a high-accuracy face detection engine.
- **MediaPipe**: Maintained and fixed errors in the MediaPipe fallback.
- **Log Cleanup**: Reduced FFmpeg console log verbosity.
