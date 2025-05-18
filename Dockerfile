FROM nixos/nix:2.9.2

# Allow root to manage Nix
RUN mkdir -p /etc/nix && \
    echo "trusted-users = root" >> /etc/nix/nix.conf

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Pre-build the environment (runs shellHook in shell.nix to install dependencies)
RUN nix-shell shell.nix --pure --run "echo Dependencies installed"

# Make scripts executable
RUN chmod +x llm-processor.py webui.py start.py shinar.py

# Default entrypoint: run start.py inside Nix shell defined by shell.nix
ENTRYPOINT ["nix-shell", "shell.nix", "--pure", "--run", "python start.py"]