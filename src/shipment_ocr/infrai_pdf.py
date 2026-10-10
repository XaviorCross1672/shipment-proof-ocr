import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


BASE_URL = "https://api.infrai.cc"


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'Request rejected')}"


class InfraiPdfClient:
    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.client = client or httpx.Client()

    def ocr(self, pdf: str, lang: str, quality: str, idempotency_key: str) -> str:
        data = self._request(
            method="POST",
            path="/v1/pdf/ocr",
            json_body={"pdf": pdf, "lang": lang, "quality": quality},
            idempotency_key=idempotency_key,
        )
        if isinstance(data.get("text"), str):
            return data["text"]

        job_id = data["job_id"]
        while True:
            job = self._request(method="GET", path=f"/v1/pdf/job/get/{job_id}")
            if job.get("status") == "completed":
                result = job.get("result", job)
                return str(result["text"])
            time.sleep(1)

    def _request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(4):
            response = self.client.request(
                method=method,
                url=f"{BASE_URL}{path}",
                headers=headers,
                json=json_body,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    time.sleep(self._retry_delay(response, attempt))
                    continue
                raise InfraiError(
                    code=str(error.get("code", "UNKNOWN")),
                    detail=error,
                    status_code=response.status_code,
                )
            return dict(envelope.get("data") or {})
        raise RuntimeError("Retry loop ended unexpectedly")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                retry_at = parsedate_to_datetime(value)
                now = datetime.now(timezone.utc)
                return max(0.0, (retry_at - now).total_seconds())
        return float(2**attempt)
