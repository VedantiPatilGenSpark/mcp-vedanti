FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir .

CMD ["mcp-vedanti"]
