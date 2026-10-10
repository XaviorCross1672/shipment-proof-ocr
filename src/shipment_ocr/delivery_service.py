import hashlib

from fastapi import FastAPI, HTTPException

from .event_modeler import model_delivery_event
from .infrai_pdf import InfraiError, InfraiPdfClient
from .models import ShipmentEvent, ShipmentOcrRequest


app = FastAPI(title="Shipment proof OCR")


@app.post("/shipments/ocr", response_model=ShipmentEvent)
def ingest_delivery_proof(request: ShipmentOcrRequest) -> ShipmentEvent:
    key_source = f"shipment-proof:{request.shipment_id}".encode()
    idempotency_key = hashlib.sha256(key_source).hexdigest()
    try:
        text = InfraiPdfClient().ocr(
            pdf=request.proof.pdf,
            lang=request.proof.language,
            quality=request.proof.quality,
            idempotency_key=idempotency_key,
        )
    except InfraiError as error:
        client_status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": error.code, "message": str(error)},
        ) from error
    return model_delivery_event(request.shipment_id, text)

