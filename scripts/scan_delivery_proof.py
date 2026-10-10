import argparse
import json

from shipment_ocr.event_modeler import model_delivery_event
from shipment_ocr.infrai_pdf import InfraiPdfClient


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR one proof of delivery")
    parser.add_argument("shipment_id")
    parser.add_argument("pdf")
    args = parser.parse_args()

    text = InfraiPdfClient().ocr(
        pdf=args.pdf,
        lang="eng",
        quality="accurate",
        idempotency_key=f"pod-{args.shipment_id}",
    )
    event = model_delivery_event(args.shipment_id, text)
    print(json.dumps(event.model_dump(), indent=2))


if __name__ == "__main__":
    main()
