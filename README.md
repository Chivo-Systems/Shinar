<div align="center">
  <img src="assets/logo.png" alt="Shinar Logo" width="120" />
  <h1>Shinar - AI Call Analytics</h1>
  <p><em>Clean, annotate, and summarize call transcripts with GPT-4.5</em></p>
</div>

Shinar is a lightweight toolchain and web UI for processing phone call transcriptions.
It watches high-fidelity transcript files, uses OpenAI’s GPT-4.xx to:

- ✨ Clean up transcription errors
- 🗣️ Infer speakers (Company, Client, or Speaker 1, Speaker 2…)
- 📝 Generate concise summaries

Results are served via a simple Flask web UI with HTTP Basic Auth.

---

## 🚀 Quick Start (Recommended)

The easiest way to run Shinar is via Docker Compose.

### Prerequisites

- Docker Engine
- Docker Compose
- A valid OpenAI API key
- `OPENAI_MODEL` for setting the model
- `WEBUI_USERNAME` & `WEBUI_PASSWORD` for web access

### Run

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/shinar.git
   cd shinar
   ```
2. Copy and configure your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and set OPENAI_API, OPENAI_MODEL (optional),
   # WEBUI_USERNAME, WEBUI_PASSWORD, etc.
   ```
3. Launch services:
   ```bash
   docker-compose up -d
   ```
4. Visit the web UI at <http://localhost:5000> and log in with your credentials.

Use `docker-compose logs -f` to follow processing output.

---

## 🛠️ NixOS / Local Development

If you prefer Nix, Shinar ships with a `shell.nix` that sets up all dependencies:

```bash
nix-shell shell.nix
source .venv/bin/activate   # Virtualenv is auto-created
./start.py                  # Boots watcher, LLM processor, and web UI
```

By default, the web UI runs on port 5000. Access via <http://localhost:5000>.

---

## ⚙️ Configuration

| Variable         | Description                                        | Default     |
|------------------|----------------------------------------------------|-------------|
| `OPENAI_API`     | Your OpenAI API key                                | (required)  |
| `OPENAI_MODEL`   | GPT model to use (e.g. `gpt-4.5`)                  | `gpt-4.5`   |
| `WEBUI_USERNAME` | Username for HTTP Basic Auth                      | (required)  |
| `WEBUI_PASSWORD` | Password for HTTP Basic Auth                      | (required)  |

Transcripts are read from `output-transcriptions/`. AI-processed
files land in `AI-Processed-Transcriptions/` and summaries in `AI-Summary/`.

---

_Docker is the recommended method for reproducible, hassle-free
deployment. The Nix shell provides a local alternative for development._

## Use

Once the container is spooled up and running, or is called directly via `start.py` (your choice) - the next step is to begin ingesting audio files. Audio files can be inserted to the `/source-audio folder`, which is actively watched by the backend process. Files can be ingested any number of ways to that folder, including Rsync, FTP/SFTP, Syncthing, and any other tool that can programmatically put a file from one place to another. Guides on integration with off-the-shelf PBX systems are coming soon.

Note: Certain regions have certain legal frameworks around data collection (EU, for example), use this tool responsibly.


