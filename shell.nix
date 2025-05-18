{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.ffmpeg
    pkgs.python3Full
    pkgs.python3Packages.pip
    # Add GCC runtime for libstdc++.so.6 support
    pkgs.gcc
  ];

  shellHook = ''
    # Ensure C++ runtime libs are visible (for torch)
    LIBSTDCXX_DIR=$(dirname $(gcc -print-file-name=libstdc++.so.6))
    # Prepend C++ runtime dir for torch
    export LD_LIBRARY_PATH=$LIBSTDCXX_DIR:$LD_LIBRARY_PATH

    # Setup Python virtual environment in .venv
    if [ ! -d .venv ]; then
      python -m venv .venv
    fi
    source .venv/bin/activate
    pip install --upgrade pip
    # Install required Python packages including Flask for the web UI
    pip install openai-whisper resemblyzer watchdog scikit-learn numpy flask openai
    # Remove unwanted backport typing package to avoid stdlib conflict
    pip uninstall -y typing || true
    echo "Virtualenv .venv activated with required Python packages"
  '';
}

