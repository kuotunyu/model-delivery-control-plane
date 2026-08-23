from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict


class SyntheticRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temp: float
    humidity: float
    hour: int


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: SyntheticRow


class PredictionResponse(BaseModel):
    prediction: float
    schema_version: str = "synthetic-v1"


app = FastAPI(title="MDCP Wave 0 Synthetic Predictor")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    row = request.row
    value = row.temp * 5.0 + row.humidity * 3.8 + row.hour * 0.5
    return PredictionResponse(prediction=round(value, 6))
