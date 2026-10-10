from typing import Literal

from pydantic import BaseModel, Field


class ProofOfDelivery(BaseModel):
    pdf: str = Field(description="Base64-encoded PDF accepted by Infrai")
    language: str = "eng"
    quality: Literal["fast", "accurate"] = "accurate"


class ShipmentOcrRequest(BaseModel):
    shipment_id: str = Field(min_length=1)
    proof: ProofOfDelivery


class ShipmentException(BaseModel):
    code: Literal["POD_DETAILS_MISSING"]
    message: str
    missing_fields: list[str]


class ShipmentEvent(BaseModel):
    shipment_id: str
    event_type: Literal["delivered", "manual_review"]
    searchable_text: str
    signed_by: str | None
    delivered_at: str | None
    exception: ShipmentException | None = None
