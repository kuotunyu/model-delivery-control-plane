from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from mdcp.contracts.workload import BikeRequest, NormalizedFloat, RequestId


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
