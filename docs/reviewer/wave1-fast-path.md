# Wave 1 reviewer fast path

This path uses only checked-in synthetic fixtures. It does not download UCI data, open H2, require
an NVIDIA GPU, contact MLflow outside a temporary local test store, or mutate a remote registry.

```powershell
uv sync --frozen --all-groups
uv run pytest tests/unit/workload tests/unit/policy tests/unit/contracts tests/contract/workload tests/integration/test_training_reproducibility.py tests/integration/test_onnx_parity.py tests/integration/test_mlflow_lineage.py -q
uv run python -m mdcp.workload.cli verify-fixtures --root tests/fixtures/artifacts
```

Expected terminal evidence:

```text
67 passed
FIXTURES PASS stable=1 candidate=1 uci_rows=0
```

The two reviewer ONNX files are deterministic analytic models, not copies of the measured UCI
models. `verify-fixtures` regenerates them in memory, compares their bytes, recomputes both canonical
artifact-descriptor digests, checks the serving inventory, and recomputes the 2,400-row synthetic H1
PASS with the frozen calendar-day bootstrap. Natural H1 remains separate measured evidence and is
currently `FAIL`; the synthetic PASS cannot make the measured candidate eligible for promotion.
