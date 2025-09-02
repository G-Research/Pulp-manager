# Use Microsoft's Python devcontainer base image with Python 3.10 for compatibility
FROM mcr.microsoft.com/devcontainers/python:3.10-bookworm

# Switch to root to install system dependencies
USER root

# Install system dependencies matching the main Dockerfile plus dev tools
RUN apt-get update && apt-get install -y \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    default-libmysqlclient-dev \
    libpq-dev \
    postgresql-client \
    netcat-openbsd \
    mariadb-client \
    redis-tools \
    vim \
    emacs-nox \
    fzf \
    nano \
    ripgrep \
    htop \
    net-tools \
    iputils-ping \
    dnsutils \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python testing and development packages globally with specific versions
RUN pip install --no-cache-dir \
    pytest==7.4.4 \
    pytest-asyncio==0.21.1 \
    pytest-env==1.1.3 \
    coverage==7.3.2 \
    pylint==3.0.0 \
    black \
    isort==5.12.0 \
    flake8

# Set up workspace directory and ensure it exists with correct permissions
RUN mkdir -p /workspace && chown -R vscode:vscode /workspace
WORKDIR /workspace

# Don't set USER in Dockerfile - let devcontainer.json handle it
# USER vscode

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Default command
CMD ["/bin/bash"]