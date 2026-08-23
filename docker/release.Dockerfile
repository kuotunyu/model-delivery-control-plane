ARG MDCP_PYTHON_IMAGE=python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2
FROM ${MDCP_PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    MDCP_ONNX_PATH=/model/model.onnx \
    MDCP_DESCRIPTOR_PATH=/model/artifact-descriptor.json

RUN groupadd --gid 10001 mdcp \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent mdcp
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN python -m pip install --no-cache-dir uv==0.8.13 \
    && uv sync --frozen --no-dev --group runtime --group ml
COPY src ./src
COPY .release-model/model.onnx /model/model.onnx
COPY .release-model/artifact-descriptor.json /model/artifact-descriptor.json

USER 10001:10001
EXPOSE 8080
CMD ["/app/.venv/bin/uvicorn", "mdcp.predictor.app:app", "--host", "0.0.0.0", "--port", "8080"]
