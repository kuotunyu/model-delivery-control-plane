from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

RequestId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]
ReleaseId = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
NormalizedFloat = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]


class BikeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: RequestId
    season: Literal[1, 2, 3, 4]
    mnth: Annotated[int, Field(ge=1, le=12)]
    hr: Annotated[int, Field(ge=0, le=23)]
    holiday: Literal[0, 1]
    weekday: Annotated[int, Field(ge=0, le=6)]
    workingday: Literal[0, 1]
    weathersit: Literal[1, 2, 3, 4]
    temp: NormalizedFloat
    atemp: NormalizedFloat
    hum: NormalizedFloat
    windspeed: NormalizedFloat


class BikeRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["mdcp.bike-request.v2"]
    request_id: RequestId
    event_timestamp: Annotated[str, StringConstraints(min_length=25, max_length=35)]
    season: Literal[1, 2, 3, 4]
    mnth: Annotated[int, Field(ge=1, le=12)]
    hr: Annotated[int, Field(ge=0, le=23)]
    holiday: Literal[0, 1]
    weekday: Annotated[int, Field(ge=0, le=6)]
    workingday: Literal[0, 1]
    weathersit: Literal[1, 2, 3, 4]
    temp: NormalizedFloat
    atemp: NormalizedFloat
    hum: NormalizedFloat
    windspeed: NormalizedFloat

    def to_legacy(self) -> BikeRequest:
        return BikeRequest.model_validate(
            self.model_dump(exclude={"schema_version", "event_timestamp"})
        )


BikeRequestEnvelope = BikeRequest | BikeRequestV2


class PredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: RequestId
    release_id: ReleaseId
    prediction: Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
    route_revision: Annotated[int, Field(gt=0)]
    traceparent: str | None = None


class SafeErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: RequestId | None = None
    error_code: Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")]
    retryable: bool = False
