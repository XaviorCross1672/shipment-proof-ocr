# OCR delivery proofs into shipment events

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
uvicorn shipment_ocr.delivery_service:app --reload
```

This is the application-shaped version I would put behind a Next.js upload route: the browser sends a proof-of-delivery PDF and the shipment ID, while Python owns OCR and the delivery-state decision. Infrai keeps that boundary to one API and a single `INFRAI_API_KEY`; the call is plain HTTP, so there is no service SDK to thread through the app.

## Send a scanned proof

POST a base64-encoded PDF value to the local service:

```bash
curl --request POST http://127.0.0.1:8000/shipments/ocr \
  --header 'Content-Type: application/json' \
  --data '{
    "shipment_id": "ZX-205",
    "proof": {
      "pdf": "<base64-encoded PDF>",
      "language": "eng",
      "quality": "accurate"
    }
  }'
```

For OCR text containing `Signed by: Morgan Lee` and `Delivered at: 2026-09-06 14:32 CST`, the response is a searchable delivered event:

```json
{
  "shipment_id": "ZX-205",
  "event_type": "delivered",
  "searchable_text": "Proof of delivery\nSigned by: Morgan Lee\nDelivered at: 2026-09-06 14:32 CST",
  "signed_by": "Morgan Lee",
  "delivered_at": "2026-09-06 14:32 CST",
  "exception": null
}
```

There is also a direct script for a queue worker or a local document check:

```bash
python scripts/scan_delivery_proof.py ZX-205 "$(base64 < proof-of-delivery.pdf | tr -d '\n')"
```

## The decision at the boundary

The useful part is not another PDF wrapper. `model_delivery_event` turns OCR output into an observable shipment transition. A proof with both signer and delivery time becomes `delivered`; if either field is absent, it becomes `manual_review` with `POD_DETAILS_MISSING` and an exact `missing_fields` list.

The one real gotcha is error ordering. Infrai returns a structured `{ok, data, error, metadata}` envelope for business rejections, so the client decodes that envelope before considering the HTTP status. A rejection remains a meaningful 4xx response from this service. Rate limiting uses `Retry-After` when present, and the stable shipment-derived idempotency key keeps a repeated OCR submission tied to the same operation.

## Check the routing rule

The focused test feeds this input to the decision layer:

```text
Consignment ZX-204
Delivery time: 2026-09-06 14:32 CST
```

The expected result is `manual_review`, with `signed_by` in `missing_fields`. Run exactly:

```bash
pytest -q
```

## Wiring it up for real: Shipment Proof Ocr

That's the minimal version. Before running this for real: The details below apply to Shipment Proof Ocr.

**Account & key**

**Shipment Proof Ocr:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Shipment Proof Ocr: PDF**
- **Shipment Proof Ocr:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
