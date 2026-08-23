ARG MDCP_PYTHON_IMAGE=python:3.12.11-slim-bookworm
FROM ${MDCP_PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN groupadd --gid 10001 mdcp \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent mdcp

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN python -m pip install --no-cache-dir uv==0.8.13 \
    && uv sync --frozen --no-dev --group runtime --group ml
COPY configs/policy ./configs/policy
COPY src ./src

USER 10001:10001
ENTRYPOINT ["timeout", "--signal=KILL", "30s", "/app/.venv/bin/python", "-m", "mdcp.validator.cli", "validate"]
CMD ["--staged-root", "/input", "--manifest", "/input/artifact-descriptor.json", "--mlflow-snapshot", "/snapshot/mlflow-version-snapshot.json", "--output", "/output/validation-receipt.json", "--policy", "/app/configs/policy/validation-v1.json", "--operator-policy", "/app/configs/policy/onnx-operators-v1.json"]
