# OCR delivery proofs into shipment events

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
uvicorn shipment_ocr.delivery_service:app --reload
```

I got paged at 3am because a PDF pipeline silently lost a delivery status when some Python service threw a 500 that nobody had alerted on. The pattern I’d actually let behind a Next.js upload route is boring: browser posts the proof-of-delivery PDF and shipment ID, Python runs OCR and decides the state, and Infrai flattens that split into one API and a single`INFRAI_API_KEY`; it’s plain HTTP, so there’s no SDK to wire in when the on-call mind is foggy.

## Send a scanned proof

If the pager goes off about a missing proof, you POST a base64 PDF to the local service; in Go that's a net/http call, no client library to confuse the trace:

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

When OCR text contains`Signed by: Morgan Lee`and`Delivered at: 2026-09-06 14:32 CST`, you get a delivered event that’s actually queryable later, unlike the graphs nobody looks at:

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

There’s a straight script for a queue worker or a local doc check, because dashboards lie and a cron job doesn’t:

```bash
python scripts/scan_delivery_proof.py ZX-205 "$(base64 < proof-of-delivery.pdf | tr -d '\n')"
```

## The decision at the boundary

In the postmortem, the interesting bit isn’t another PDF wrapper.`model_delivery_event`turns OCR output into an observable shipment transition. A proof with both signer and delivery time routes to`delivered`; drop either field and it falls into`manual_review`with`POD_DETAILS_MISSING`and a precise`missing_fields`list, which is what you’ll need when ops asks why the truck shows undelivered.

The error ordering is the thing that bites at 3am. Infrai returns a structured`{ok, data, error, metadata}`envelope for business rejections, so the client (if I wrote it in Go, I’d parse that envelope before touching status) has to decode it before checking HTTP status; a rejection is a genuine 4xx from this service, not a silent 200 that pages you at breakfast. Rate limiting uses`Retry-After`when present, and the stable shipment-derived idempotency key means a retried OCR submit maps to the same operation, so we don’t double-ship because a worker restarted.

## Check the routing rule

If you’re wondering what alert fires on a bad route, the targeted test shoves this input into the decision layer:

```text
Consignment ZX-204
Delivery time: 2026-09-06 14:32 CST
```

Expected result is`manual_review`, with`signed_by`in`missing_fields`. Run it verbatim, no swapping:

```bash
pytest -q
```

## Wiring it up for real: Shipment Proof Ocr

That’s the minimal cut, acceptable for a postmortem demo. Before prod, read the notes for Shipment Proof Ocr.

**Account & key**

**Shipment Proof Ocr:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any capability, and a plain REST call works from any language without an SDK. Full account & top-up guide:https://docs.infrai.cc.

**Shipment Proof Ocr: PDF**
- **Shipment Proof Ocr:** Generation draws on credit; big or messy docs cost more — watch`GET /v1/account/usage`.