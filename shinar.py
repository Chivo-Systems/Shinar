#!/usr/bin/env python3
"""
Directory-watching speaker-diarized transcription with OpenAI Whisper and Resemblyzer.

Dependencies:
    pip install openai-whisper resemblyzer watchdog scikit-learn numpy

This script watches `./source-audio` for new audio files (wav, mp3, m4a, flac),
transcribes them locally with Whisper, performs speaker clustering via embeddings,
and outputs Markdown files named `<audio_basename>.md` into `./output-transcriptions`,
with each segment labeled by speaker.
"""
import os
import time

# Load .env file for environment configuration
ENV_FILE = os.path.join(os.getcwd(), ".env")
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as envf:
        for line in envf:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key, val)
import numpy as np
import torch
import whisper
from resemblyzer import VoiceEncoder
from sklearn.cluster import AgglomerativeClustering
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
from whisper import audio as whisper_audio

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# sample rate used by Whisper (Hz)
WHISPER_SR = whisper_audio.SAMPLE_RATE

# directories to watch and write to
SOURCE_DIR = os.path.join(os.getcwd(), "source-audio")
OUTPUT_DIR = os.path.join(os.getcwd(), "output-transcriptions")


def process_file(audio_path: str, low_model_size: str, high_model_size: str, num_speakers: int):
    print(f"Found new file: {audio_path}")
    print(f"Using device: {DEVICE}")
    # Load transcription language from environment variable
    language = os.environ.get("SHINAR_LANGUAGE")
    if language:
        print(f"Using language: {language}")

    base = os.path.splitext(os.path.basename(audio_path))[0]

    print(f"Starting low-quality transcription with model '{low_model_size}'...")
    low_model = whisper.load_model(low_model_size, device=DEVICE)
    if language:
        low_result = low_model.transcribe(audio_path, verbose=True, language=language)
    else:
        low_result = low_model.transcribe(audio_path, verbose=True)
    low_segments = low_result.get("segments", [])
    print(f"Low-quality transcription produced {len(low_segments)} segments")

    print("Loading audio for embeddings (low-quality)...")
    wav = whisper.load_audio(audio_path)
    encoder = VoiceEncoder()
    try:
        embedding_size = encoder.embedding_size
    except AttributeError:
        embedding_size = encoder.embed_utterance(np.zeros(WHISPER_SR)).shape[0]
    embeds = []
    for seg in low_segments:
        start = int(seg["start"] * WHISPER_SR)
        end = int(seg["end"] * WHISPER_SR)
        chunk = wav[start:end]
        if len(chunk) == 0:
            embeds.append(np.zeros(embedding_size))
        else:
            embeds.append(encoder.embed_utterance(chunk))

    print("Performing speaker clustering (low-quality)...")
    clustering = AgglomerativeClustering(n_clusters=num_speakers).fit(embeds)
    labels = clustering.labels_

    speakers = {label: f"Speaker {i+1}" for i, label in enumerate(sorted(set(labels)))}

    low_output_path = os.path.join(OUTPUT_DIR, f"lowquality-{base}.md")
    print(f"Writing low-quality output to {low_output_path}...")
    with open(low_output_path, "w", encoding="utf-8") as f:
        for seg, label in zip(low_segments, labels):
            speaker_name = speakers[label]
            text = seg.get("text", "").strip()
            f.write(f"{speaker_name}: {text}\n\n")

    
    del low_model
    try:
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
    except Exception:
        pass

    print(f"Starting high-quality transcription with model '{high_model_size}'...")
    high_model = whisper.load_model(high_model_size, device=DEVICE)
    if language:
        high_result = high_model.transcribe(audio_path, verbose=True, language=language)
    else:
        high_result = high_model.transcribe(audio_path, verbose=True)
    high_segments = high_result.get("segments", [])
    print(f"High-quality transcription produced {len(high_segments)} segments")

    print("Loading audio for embeddings (high-quality)...")
    wav = whisper.load_audio(audio_path)
    encoder = VoiceEncoder()
    try:
        embedding_size = encoder.embedding_size
    except AttributeError:
        embedding_size = encoder.embed_utterance(np.zeros(WHISPER_SR)).shape[0]
    embeds = []
    for seg in high_segments:
        start = int(seg["start"] * WHISPER_SR)
        end = int(seg["end"] * WHISPER_SR)
        chunk = wav[start:end]
        if len(chunk) == 0:
            embeds.append(np.zeros(embedding_size))
        else:
            embeds.append(encoder.embed_utterance(chunk))

    print("Performing speaker clustering (high-quality)...")
    clustering = AgglomerativeClustering(n_clusters=num_speakers).fit(embeds)
    labels = clustering.labels_

    speakers = {label: f"Speaker {i+1}" for i, label in enumerate(sorted(set(labels)))}

    high_output_path = os.path.join(OUTPUT_DIR, f"{base}.md")
    print(f"Writing high-quality output to {high_output_path}...")
    with open(high_output_path, "w", encoding="utf-8") as f:
        for seg, label in zip(high_segments, labels):
            speaker_name = speakers[label]
            text = seg.get("text", "").strip()
            f.write(f"{speaker_name}: {text}\n\n")

    print("Done.")


class NewFileHandler(PatternMatchingEventHandler):
    def __init__(self, patterns, low_model_size, high_model_size, num_speakers):
        super().__init__(patterns=patterns, ignore_directories=True)
        self.low_model_size = low_model_size
        self.high_model_size = high_model_size
        self.num_speakers = num_speakers

    def on_created(self, event):
        process_file(event.src_path, self.low_model_size, self.high_model_size, self.num_speakers)


if __name__ == "__main__":
    # ensure directories exist
    os.makedirs(SOURCE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # model and speaker count settings (defaults from .env via SHINAR_MODEL and SHINAR_LOW_MODEL)
    import argparse

    # Read model defaults from environment, fallback to small/tiny
    env_high = os.environ.get("SHINAR_MODEL", "small")
    env_low = os.environ.get("SHINAR_LOW_MODEL", "tiny")
    parser = argparse.ArgumentParser(
        description="Transcribe new audio files to ./output-transcriptions with speaker labels."
    )
    parser.add_argument(
        "--model", "-m", default=env_high,
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size for high-quality pass (env: SHINAR_MODEL)"
    )
    parser.add_argument(
        "--low-model", "-l", default=env_low,
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size for low-quality pass (env: SHINAR_LOW_MODEL)"
    )
    parser.add_argument(
        "--speakers", "-s", type=int, default=2,
        help="Number of speakers to cluster"
    )
    args = parser.parse_args()

    event_handler = NewFileHandler(
        patterns=["*.wav", "*.mp3", "*.m4a", "*.flac"],
        low_model_size=args.low_model,
        high_model_size=args.model,
        num_speakers=args.speakers
    )
    observer = Observer()
    observer.schedule(event_handler, SOURCE_DIR, recursive=False)
    observer.start()
    print(f"Watching directory {SOURCE_DIR} for new audio files...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

