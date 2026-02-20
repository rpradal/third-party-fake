from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import socket
import time
from typing import Any, Literal, Optional
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl


class Customer(BaseModel):
    id: str = Field(..., description="Third-party internal id")
    archived: bool = False
    payment_term: Optional[Literal["Net 30", "Net 60"]] = None


class UpdateCustomerRequest(BaseModel):
    archived: Optional[bool] = None
    payment_term: Optional[Literal["Net 30", "Net 60"]] = None


class WebhookConfigRequest(BaseModel):
    webhook_url: HttpUrl


class WebhookAttempt(BaseModel):
    at: datetime
    customer_id: str
    webhook_url: Optional[str]
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None


class InboundAttempt(BaseModel):
    at: datetime
    method: str
    path: str
    payload: Any
    success: bool
    status_code: int
    error: Optional[str] = None


class AppState(BaseModel):
    webhook_url: Optional[str]
    customers: list[Customer]
    webhook_attempts: list[WebhookAttempt]
    inbound_attempts: list[InboundAttempt]


app = FastAPI(title="Fake Third Party Demo", version="1.0.0")
logger = logging.getLogger("fake_third_party_demo")
FRONTEND_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(FRONTEND_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SEED_CUSTOMERS: list[Customer] = [
    Customer(id="hs-001", archived=False, payment_term="Net 30"),
    Customer(id="hs-002", archived=False, payment_term=None),
    Customer(id="hs-003", archived=True, payment_term=None),
]

customers_by_id: dict[str, Customer] = {customer.id: customer for customer in SEED_CUSTOMERS}
webhook_url: Optional[str] = "http://localhost:8001/api/webhooks/third-party/sync"
webhook_attempts: list[WebhookAttempt] = []
inbound_attempts: list[InboundAttempt] = []


@app.middleware("http")
async def track_inbound_attempts(request: Request, call_next):
    global inbound_attempts

    origin = request.headers.get("origin")
    is_front_request = origin in FRONTEND_ORIGINS
    should_track = request.method in {"POST", "PUT", "PATCH"} and not is_front_request
    payload: Any = None
    body = b""

    if should_track:
        body = await request.body()
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:  # noqa: BLE001
                payload = body.decode("utf-8", errors="replace")

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(request.scope, receive)

    status_code = 500
    success = False
    error: Optional[str] = None

    try:
        response = await call_next(request)
        status_code = response.status_code
        success = response.status_code < 400
        return response
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        raise
    finally:
        if should_track:
            inbound_attempts = (
                inbound_attempts
                + [
                    InboundAttempt(
                        at=datetime.now(timezone.utc),
                        method=request.method,
                        path=request.url.path,
                        payload=payload,
                        success=success,
                        status_code=status_code,
                        error=error,
                    )
                ]
            )[-50:]


async def notify_erp_webhook(customer: Customer) -> None:
    global webhook_attempts

    if not webhook_url:
        logger.warning("Webhook skipped: no webhook configured for customer_id=%s", customer.id)
        webhook_attempts = (
            webhook_attempts
            + [
                WebhookAttempt(
                    at=datetime.now(timezone.utc),
                    customer_id=customer.id,
                    webhook_url=None,
                    success=False,
                    error="No webhook configured",
                )
            ]
        )[-30:]
        return

    payload = {
        "provider": "hubspot",
        "model": "customer",
        "external_ids": [customer.id],
    }

    try:
        parsed = urlsplit(webhook_url)
        host = parsed.hostname
        scheme = parsed.scheme
        port = parsed.port or (443 if scheme == "https" else 80)
        if host:
            try:
                addresses = sorted(
                    {
                        item[4][0]
                        for item in socket.getaddrinfo(
                            host,
                            port,
                            type=socket.SOCK_STREAM,
                        )
                    }
                )
                logger.info(
                    "Webhook DNS resolved: host=%s port=%s addresses=%s",
                    host,
                    port,
                    addresses,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Webhook DNS resolution failed: host=%s port=%s url=%r error=%s",
                    host,
                    port,
                    webhook_url,
                    exc,
                )

        start = time.monotonic()
        logger.info(
            "Sending webhook: customer_id=%s webhook_url=%r provider=%s model=%s external_ids=%s",
            customer.id,
            webhook_url,
            payload["provider"],
            payload["model"],
            payload["external_ids"],
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(webhook_url, json=payload)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        response_excerpt = response.text[:200].replace("\n", "\\n")
        logger.info(
            "Webhook response: customer_id=%s status=%s success=%s elapsed_ms=%s body_excerpt=%r",
            customer.id,
            response.status_code,
            response.is_success,
            elapsed_ms,
            response_excerpt,
        )
        webhook_attempts = (
            webhook_attempts
            + [
                WebhookAttempt(
                    at=datetime.now(timezone.utc),
                    customer_id=customer.id,
                    webhook_url=webhook_url,
                    success=response.is_success,
                    status_code=response.status_code,
                    error=None if response.is_success else response.text[:200],
                )
            ]
        )[-30:]
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Webhook error: customer_id=%s webhook_url=%s error=%s",
            customer.id,
            webhook_url,
            exc,
        )
        webhook_attempts = (
            webhook_attempts
            + [
                WebhookAttempt(
                    at=datetime.now(timezone.utc),
                    customer_id=customer.id,
                    webhook_url=webhook_url,
                    success=False,
                    error=str(exc),
                )
            ]
        )[-30:]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/customers", response_model=list[Customer])
def list_customers() -> list[Customer]:
    return sorted(customers_by_id.values(), key=lambda c: c.id)


@app.get("/customers/{customer_id}", response_model=Customer)
def get_customer(customer_id: str) -> Customer:
    customer = customers_by_id.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.patch("/customers/{customer_id}", response_model=Customer)
async def update_customer_from_fake_third_party(
    customer_id: str, payload: UpdateCustomerRequest
) -> Customer:
    existing = customers_by_id.get(customer_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Customer not found")

    updated = existing.model_copy(
        update={
            "archived": payload.archived if payload.archived is not None else existing.archived,
            "payment_term": (
                payload.payment_term
                if "payment_term" in payload.model_fields_set
                else existing.payment_term
            ),
        }
    )
    customers_by_id[customer_id] = updated

    await notify_erp_webhook(updated)
    return updated


@app.post("/customers/{customer_id}/call-erp", response_model=Customer)
async def call_erp_for_customer(customer_id: str) -> Customer:
    customer = customers_by_id.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    await notify_erp_webhook(customer)
    return customer


@app.post("/webhook/config")
def set_webhook_config(payload: WebhookConfigRequest) -> dict[str, str]:
    global webhook_url
    webhook_url = str(payload.webhook_url).strip()
    logger.info("Webhook configuration updated: webhook_url=%r", webhook_url)
    return {"webhook_url": webhook_url}


@app.get("/state", response_model=AppState)
def get_state() -> AppState:
    return AppState(
        webhook_url=webhook_url,
        customers=sorted(customers_by_id.values(), key=lambda c: c.id),
        webhook_attempts=list(reversed(webhook_attempts)),
        inbound_attempts=list(reversed(inbound_attempts)),
    )
