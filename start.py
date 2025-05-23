#!/usr/bin/env python3
"""
Entrypoint to run both the shinar watcher and the web UI.

Usage:
  start.py [shinar args...]

Any arguments are forwarded to shinar.py.
"""
import os
import signal
import subprocess
import sys
import time


def main():
    """
    Launch shinar.py (audio watcher) and webui.py (Flask front-end) concurrently.
    """
    base_dir = os.path.dirname(__file__)
    shinar_path = os.path.join(base_dir, 'shinar.py')
    webui_path = os.path.join(base_dir, 'webui.py')
    if not os.path.isfile(shinar_path):
        print(f"Error: shinar.py not found at {shinar_path}", file=sys.stderr)
        return 1
    if not os.path.isfile(webui_path):
        print(f"Error: webui.py not found at {webui_path}", file=sys.stderr)
        return 1

    python = sys.executable
    # Commands for processes
    shinar_cmd = [python, shinar_path] + sys.argv[1:]
    webui_cmd = [python, webui_path]
    # LLM processor
    llm_path = os.path.join(base_dir, 'llm-processor.py')
    if not os.path.isfile(llm_path):
        print(f"Error: llm-processor.py not found at {llm_path}", file=sys.stderr)
        return 1
    llm_cmd = [python, llm_path]

    p_shinar = subprocess.Popen(shinar_cmd)
    p_webui = subprocess.Popen(webui_cmd)
    p_llm = subprocess.Popen(llm_cmd)

    def shutdown(sig=None, frame=None):
        for p in (p_shinar, p_webui, p_llm):
            try:
                p.terminate()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait until either process exits
    try:
        while True:
            time.sleep(1)
            if (p_shinar.poll() is not None or
                p_webui.poll() is not None or
                p_llm.poll() is not None):
                break
    except KeyboardInterrupt:
        pass
    shutdown()


if __name__ == '__main__':
    sys.exit(main())