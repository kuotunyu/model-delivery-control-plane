FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MDCP_ONNX_PATH=/model/model.onnx \
    MDCP_DESCRIPTOR_PATH=/model/artifact-descriptor.json

RUN groupadd --system mdcp && useradd --system --gid mdcp --home-dir /nonexistent mdcp
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN python -m pip install --no-cache-dir uv==0.8.13 \
    && uv sync --frozen --no-dev --group runtime --group ml
COPY src ./src

USER mdcp
EXPOSE 8080
CMD ["/app/.venv/bin/uvicorn", "mdcp.predictor.app:app", "--host", "0.0.0.0", "--port", "8080"]
