FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt requirements-dev.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements-dev.txt \
    && rm /tmp/requirements.txt /tmp/requirements-dev.txt

WORKDIR /workspaces/MCP_Vedanti
