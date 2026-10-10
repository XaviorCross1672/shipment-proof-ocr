from shipment_ocr.event_modeler import model_delivery_event


def test_missing_signature_routes_proof_to_manual_review() -> None:
    text = "Consignment ZX-204\nDelivery time: 2026-09-06 14:32 CST"

    event = model_delivery_event("ZX-204", text)

    assert event.event_type == "manual_review"
    assert event.delivered_at == "2026-09-06 14:32 CST"
    assert event.signed_by is None
    assert event.exception is not None
    assert event.exception.missing_fields == ["signed_by"]


def test_complete_proof_becomes_delivered_event() -> None:
    text = (
        "Proof of delivery\n"
        "Signed by: Morgan Lee\n"
        "Delivered at: 2026-09-06 14:32 CST"
    )

    event = model_delivery_event("ZX-205", text)

    assert event.event_type == "delivered"
    assert event.signed_by == "Morgan Lee"
    assert event.exception is None

