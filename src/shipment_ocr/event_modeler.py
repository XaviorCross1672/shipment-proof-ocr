import re

from .models import ShipmentEvent, ShipmentException


SIGNER_PATTERN = re.compile(
    r"(?:signed\s+by|received\s+by|recipient)\s*[:\-]\s*(?P<value>[^\n\r]+)",
    re.IGNORECASE,
)
DELIVERED_PATTERN = re.compile(
    r"(?:delivered\s+at|delivery\s+time)\s*[:\-]\s*(?P<value>[^\n\r]+)",
    re.IGNORECASE,
)


def model_delivery_event(shipment_id: str, searchable_text: str) -> ShipmentEvent:
    signed_by = _capture(SIGNER_PATTERN, searchable_text)
    delivered_at = _capture(DELIVERED_PATTERN, searchable_text)
    missing = []
    if signed_by is None:
        missing.append("signed_by")
    if delivered_at is None:
        missing.append("delivered_at")

    if missing:
        exception = ShipmentException(
            code="POD_DETAILS_MISSING",
            message="Proof of delivery needs a document review.",
            missing_fields=missing,
        )
        event_type = "manual_review"
    else:
        exception = None
        event_type = "delivered"

    return ShipmentEvent(
        shipment_id=shipment_id,
        event_type=event_type,
        searchable_text=searchable_text.strip(),
        signed_by=signed_by,
        delivered_at=delivered_at,
        exception=exception,
    )


def _capture(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group("value").strip() if match else None

