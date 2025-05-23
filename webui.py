#!/usr/bin/env python3
"""
Web UI for Shinar speaker-diarized transcriptions.
"""
import os
# Load .env for environment variables (e.g., WEBUI_USERNAME, WEBUI_PASSWORD)
ENV_FILE = os.path.join(os.getcwd(), '.env')
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as envf:
        for line in envf:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, val = line.split('=', 1)
            val = val.strip()
            # Strip surrounding quotes if present
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            os.environ.setdefault(key, val)

from flask import Flask, render_template_string, abort, jsonify, request, Response
from datetime import datetime
import subprocess
# Directory containing transcription Markdown files
OUTPUT_DIR = os.path.join(os.getcwd(), 'output-transcriptions')
# Directory containing original audio files
SOURCE_DIR = os.path.join(os.getcwd(), 'source-audio')
# Directory containing AI-processed transcripts
AI_DIR = os.path.join(os.getcwd(), 'AI-Processed-Transcriptions')
# Directory containing AI-generated summaries
SUMMARY_DIR = os.path.join(os.getcwd(), 'AI-Summary')

app = Flask(__name__, static_folder='assets', static_url_path='/assets')

# HTTP Basic Auth using WEBUI_USERNAME and WEBUI_PASSWORD from environment
USERNAME = os.environ.get('WEBUI_USERNAME')
PASSWORD = os.environ.get('WEBUI_PASSWORD')

def check_auth(user, pwd):
    return user == USERNAME and pwd == PASSWORD

def authenticate():
    return Response(
        'Login required',
        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

@app.before_request
def require_basic_auth():
    # Allow access to static assets and logout page
    if request.path.startswith(app.static_url_path) or request.path == '/logout':
        return
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

def get_calls():
    """
    Discover all calls based on markdown files in OUTPUT_DIR.
    Returns a sorted list of base call names.
    """
    if not os.path.isdir(OUTPUT_DIR):
        return []
    calls = set()
    for fname in os.listdir(OUTPUT_DIR):
        if not fname.endswith('.md'):
            continue
        if fname.startswith('lowquality-'):
            base = fname[len('lowquality-'):-3]
        else:
            base = fname[:-3]
        if base:
            calls.add(base)
    return sorted(calls)

def get_call_info():
    """
    Return list of calls with file creation timestamps.
    """
    bases = get_calls()
    info = []
    for base in bases:
        # locate the original audio file
        audio_path = None
        for ext in ('.wav', '.mp3', '.m4a', '.flac'):
            p = os.path.join(SOURCE_DIR, base + ext)
            if os.path.isfile(p):
                audio_path = p
                break
        if audio_path:
            ts = os.path.getctime(audio_path)
            # American date format (MM/DD/YYYY) with 12-hour time and AM/PM
            start = datetime.fromtimestamp(ts).strftime('%m/%d/%Y %I:%M:%S %p')
            # Compute duration via ffprobe
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'error',
                     '-show_entries', 'format=duration',
                     '-of', 'default=noprint_wrappers=1:nokey=1',
                     audio_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                dur = float(result.stdout.strip())
                hours, rem = divmod(dur, 3600)
                minutes, seconds = divmod(rem, 60)
                duration = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            except Exception:
                duration = 'Unknown'
        else:
            start = 'Unknown'
            duration = 'Unknown'
        # Check if AI-processed transcript exists
        ai_path = os.path.join(AI_DIR, f"{base}.md")
        ai_exists = os.path.isfile(ai_path)
        # Check if AI summary exists
        summary_path = os.path.join(SUMMARY_DIR, f"{base}.md")
        summary_exists = os.path.isfile(summary_path)
        info.append({
            'name': base,
            'start': start,
            'duration': duration,
            'ai_exists': ai_exists,
            'summary_exists': summary_exists
        })
    return info

@app.route('/')
def index():
    calls = get_call_info()
    return render_template_string(TEMPLATE, calls=calls)

# Simple logout page template
LOGOUT_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Logged Out - Shinar</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<div class="container text-center mt-5">
  <h2>You have been logged out.</h2>
  <p><a href="/" class="btn btn-primary mt-3">Log in again</a></p>
</div>
</body>
</html>
'''

@app.route('/logout')
def logout():
    # Render a simple logged-out page without auth prompt
    return render_template_string(LOGOUT_TEMPLATE)

@app.route('/transcript/<quality>/<call>')
def transcript(quality, call):
    # quality: 'low', 'high', 'ai', or 'summary'
    if quality not in ('low', 'high', 'ai', 'summary'):
        abort(404)
    # Determine directory and filename
    if quality == 'low':
        dirpath = OUTPUT_DIR
        fname = f'lowquality-{call}.md'
    elif quality == 'high':
        dirpath = OUTPUT_DIR
        fname = f'{call}.md'
    elif quality == 'ai':
        dirpath = AI_DIR
        fname = f'{call}.md'
    else:  # summary
        dirpath = SUMMARY_DIR
        fname = f'{call}.md'
    path = os.path.join(dirpath, fname)
    if not os.path.isfile(path):
        abort(404)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({'content': content})

TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Shinar - AI Call Analytics</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- Font Awesome -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <!-- Custom footer styling -->
  <style>
    body { padding-bottom: 100px; }
    footer.site-footer {
      position: fixed;
      bottom: 0;
      left: 0;
      width: 100%;
      background: #f8f9fa;
      border-top: 1px solid #dee2e6;
      padding: .75rem 1rem;
      z-index: 1030;
    }
    /* Widen the transcript modal */
    .modal-dialog {
      max-width: 90%;
    }
    /* Wrap long lines in the transcript content */
    #transcriptContent {
      white-space: pre-wrap;
      word-wrap: break-word;
      overflow-wrap: break-word;
    }
  </style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light bg-light">
  <div class="container-fluid">
    <a class="navbar-brand" href="#">
      <img src="{{ url_for('static', filename='logo.png') }}" alt="Shinar" height="30">
    </a>
    <div class="d-flex align-items-center">
      <a class="nav-link" href="https://github.com/" target="_blank">
        <i class="fab fa-github fa-lg"></i>
      </a>
      <a class="btn btn-sm btn-outline-danger ms-2" href="/logout">Logout</a>
    </div>
  </div>
</nav>
<div class="container mt-4">
  <h2>Calls</h2>
  {% for call in calls %}
  <div class="card mb-3">
    <div class="card-body d-flex justify-content-between align-items-center">
      <div>
        <h5 class="card-title mb-1">{{ call.name }}</h5>
        <p class="card-subtitle text-muted mb-0">Call Started: {{ call.start }} | Call Duration: {{ call.duration }}</p>
      </div>
      <div>
        <a href="#" class="btn btn-sm btn-outline-primary transcript-link me-2" data-call="{{ call.name }}" data-quality="low">Low Fidelity Transcription</a>
        <a href="#" class="btn btn-sm btn-outline-secondary transcript-link" data-call="{{ call.name }}" data-quality="high">High Fidelity Transcription</a>
        {% if call.ai_exists %}
        <br>
        <a href="#" class="btn btn-sm btn-outline-success transcript-link mt-2" data-call="{{ call.name }}" data-quality="ai">AI Processed Transcription</a>
        {% endif %}
        {% if call.summary_exists %}
        <br>
        <a href="#" class="btn btn-sm btn-outline-info transcript-link mt-2" data-call="{{ call.name }}" data-quality="summary">AI Summary</a>
        {% endif %}
      </div>
    </div>
  </div>
  {% endfor %}
</div>
<footer class="site-footer text-center text-muted">
  <small>Made With Love by The Team at <a href="https://chivo.systems" target="_blank">Chivo Systems</a></small>
</footer>
<!-- Modal -->
<div class="modal fade" id="transcriptModal" tabindex="-1" aria-labelledby="transcriptModalLabel" aria-hidden="true">
<div class="modal-dialog modal-xl modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="transcriptModalLabel">Transcript</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <pre id="transcriptContent"></pre>
      </div>
    </div>
  </div>
</div>
<!-- Bootstrap JS Bundle -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {
  var modal = new bootstrap.Modal(document.getElementById('transcriptModal'));
  document.querySelectorAll('.transcript-link').forEach(function(elem) {
    elem.addEventListener('click', function(evt) {
      evt.preventDefault();
      var call = this.dataset.call;
      var quality = this.dataset.quality;
      fetch(`/transcript/${quality}/${encodeURIComponent(call)}`)
        .then(function(resp) {
          if (!resp.ok) throw new Error('Network response was not ok');
          return resp.json();
        })
        .then(function(data) {
          var qualityLabel;
          if (quality === 'low') {
            qualityLabel = 'Low Fidelity';
          } else if (quality === 'high') {
            qualityLabel = 'High Fidelity';
          } else if (quality === 'ai') {
            qualityLabel = 'AI Processed';
          } else if (quality === 'summary') {
            qualityLabel = 'AI Summary';
          } else {
            qualityLabel = quality;
          }
          document.getElementById('transcriptModalLabel').textContent = call + ' - ' + qualityLabel;
          document.getElementById('transcriptContent').textContent = data.content;
          modal.show();
        })
        .catch(function(err) {
          console.error(err);
          alert('Failed to load transcript');
        });
    });
  });
});
</script>
</body>
</html>
'''

if __name__ == '__main__':
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)