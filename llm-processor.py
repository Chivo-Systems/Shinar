#!/usr/bin/env python3
"""
LLM Processor: watches high-quality transcripts and processes them via OpenAI GPT to clean and annotate.
"""
import os
import sys
import time
import signal
import subprocess

# Load .env for API key
ENV_FILE = os.path.join(os.getcwd(), ".env")
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as envf:
        for line in envf:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key, val)

import openai
from openai import OpenAI

# Directories and model config
OUTPUT_DIR = os.path.join(os.getcwd(), 'output-transcriptions')
# Directory for AI-processed transcripts
AI_DIR = os.path.join(os.getcwd(), 'AI-Processed-Transcriptions')
# Directory for summaries
SUMMARY_DIR = os.path.join(os.getcwd(), 'AI-Summary')

os.makedirs(AI_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# LLM model name to use (can be set in .env as OPENAI_MODEL)
MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4.5')
PROMPT = ("You are analyzing phone calls, these are transcriptions from a call. "
          "There may be mistakes as a result of the call quality. Do your best to fix these mistakes based on the context of the call. "
          "Additionally, you will attempt to infer the speakers of the call, either as Speaker X (X being a number) or as Company and Client if it is a sales, or a name if you can determine the name based on the provided context of the call. "
          "Additionally, if you can determine Company and Client and name. For example; Company James, and Client Billy - that is best. "
          "However, never put incorrect information beyond the information you are provided to preserve the integrity of the call transcription. "
          "IF there are many lines of the same repeated words over and over again, simply remove those as they may be an audio processing bug. "
          "Only respond with the call transcription and nothing else.")
# Prompt for summarization phase
SUMMARY_PROMPT = (
    "You are an AI Call Analytics Agent. You are analyzing a call transcript and you will summarize the call, "
    "including who was in the call, what the purpose of the call was, what was said, and the general tone of the call overall."
)

def summarize_file(base: str, client: OpenAI):
    """
    Read an AI-processed transcript and generate a summary markdown.
    """
    in_path = os.path.join(AI_DIR, f"{base}.md")
    out_path = os.path.join(SUMMARY_DIR, f"{base}.md")
    # Skip if summary already exists
    if os.path.exists(out_path):
        return
    print(f"Summarizing AI transcript for {base}...")
    with open(in_path, 'r', encoding='utf-8') as f:
        transcript = f.read()
    # Prepare summary messages
    messages = [
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": transcript}
    ]
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages
        )
        summary_text = resp.choices[0].message.content
    except Exception as e:
        print(f"OpenAI Summary API error: {e}", file=sys.stderr)
        return
    # Write summary output
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(summary_text)
    print(f"Wrote AI summary: {out_path}")

def process_file(path: str):
    basename = os.path.basename(path)
    # Skip non-markdown or any low-quality transcripts
    if not basename.endswith('.md') or 'lowquality' in basename.lower():
        return
    base = basename[:-3]
    # skip if already processed
    out_path = os.path.join(AI_DIR, f"{base}.md")
    if os.path.exists(out_path):
        return

    print(f"Processing AI for {basename}...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Prepare messages
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": content}
    ]
    # Set up OpenAI client using API key from .env
    api_key = os.environ.get('OPENAI_API')
    if not api_key:
        print("Error: OPENAI_API not set in environment.", file=sys.stderr)
        return
    client = OpenAI(api_key=api_key)

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages
        )
        ai_text = resp.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {e}", file=sys.stderr)
        return

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(ai_text)
    print(f"Wrote AI processed transcript: {out_path}")
    # Summarization phase
    summarize_file(base, client)


if __name__ == '__main__':
    # Watch OUTPUT_DIR for new high-quality transcripts
    from watchdog.observers import Observer
    from watchdog.events import PatternMatchingEventHandler

    class Handler(PatternMatchingEventHandler):
        def __init__(self):
            super().__init__(patterns=["*.md"], ignore_directories=True)

        def on_created(self, event):
            process_file(event.src_path)

    # Initial processing of existing files
    if os.path.isdir(OUTPUT_DIR):
        for fname in os.listdir(OUTPUT_DIR):
            process_file(os.path.join(OUTPUT_DIR, fname))

    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, OUTPUT_DIR, recursive=False)
    observer.start()
    print(f"Watching {OUTPUT_DIR} for transcripts to AI-process...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()