from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    version: str
    environment: str


class InternalHealthResponse(HealthResponse):
    database: Literal["ok", "not_checked"]
