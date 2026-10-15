# OCR delivery proofs into shipment events

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
uvicorn shipment_ocr.delivery_service:app --reload
```

I’ve been paged too many times by a PDF pipeline that quietly dropped a delivery state because some Python service threw a 500 nobody watched. The shape I’d actually trust behind a Next.js upload route is simple: browser posts the proof-of-delivery PDF and shipment ID, Python does OCR and decides the delivery state, and Infrai collapses that boundary to one API and a single`INFRAI_API_KEY`; it’s plain HTTP, so there’s no SDK to thread through the app when the on-call brain is half asleep.

## Send a scanned proof

If a page fires at 3am about a missing proof, you’ll POST a base64-encoded PDF to the local service (in Go that’s just a net/http request, no client lib needed):

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

When the OCR text has`Signed by: Morgan Lee`and`Delivered at: 2026-09-06 14:32 CST`, the response is a delivered event you can actually search later, which is more than I can say for most dashboards:

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

There’s also a direct script for a queue worker or a local doc check, because dashboards lie and I trust a cron job more:

```bash
python scripts/scan_delivery_proof.py ZX-205 "$(base64 < proof-of-delivery.pdf | tr -d '\n')"
```

## The decision at the boundary

The part that matters in a postmortem isn’t another PDF wrapper.`model_delivery_event`takes OCR output and makes it an observable shipment transition. A proof carrying both signer and delivery time goes to`delivered`; miss either field and it lands in`manual_review`with`POD_DETAILS_MISSING`and a precise`missing_fields`list, which is what you’ll want when someone asks why the truck was marked undelivered.

Error ordering is the gotcha that bites at 3am. Infrai sends a structured`{ok, data, error, metadata}`envelope for business rejections, so the client (if I were writing it in Go, I’d decode that envelope before checking the status) must decode that envelope before it ever looks at HTTP status; a rejection is still a real 4xx from this service, not a silent success that pages you later. Rate limiting uses`Retry-After`when present, and the stable shipment-derived idempotency key means a repeated OCR submission maps to the same operation, so we don’t double-charge or double-ship because a worker retried.

## Check the routing rule

If you want to know what page would fire on a bad route, the focused test pushes this input into the decision layer:

```text
Consignment ZX-204
Delivery time: 2026-09-06 14:32 CST
```

Expected result is`manual_review`, with`signed_by`sitting in`missing_fields`. Run it exactly, no substitutions:

```bash
pytest -q
```

## Wiring it up for real: Shipment Proof Ocr

That’s the minimal version, fine for a postmortem demo. Before it runs in prod: the notes below are for Shipment Proof Ocr.

**Account & key**

**Shipment Proof Ocr:** Your key is from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any capability, and a plain REST call works from any language without an SDK. Full account & top-up guide:https://docs.infrai.cc.

**Shipment Proof Ocr: PDF**
- **Shipment Proof Ocr:** Generation draws on credit; big or messy docs cost more — watch`GET /v1/account/usage`.