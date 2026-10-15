import os
import random
import time

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# Settings come from environment variables, so Kubernetes can change them without code changes
APP_VERSION = os.getenv("APP_VERSION", "dev")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://localhost:8001")
FAULT_ERROR_RATE = float(os.getenv("FAULT_ERROR_RATE", "0"))  # 0.3 = fail 30% of requests
FAULT_LATENCY_MS = int(os.getenv("FAULT_LATENCY_MS", "0"))  # extra delay per request
ALLOW_CRASH = os.getenv("ALLOW_CRASH") == "true"

app = FastAPI(title="api")
inventory = httpx.Client(base_url=INVENTORY_URL, timeout=2.0)

# Metrics that Prometheus will read from /metrics
REQUESTS = Counter("http_requests_total", "HTTP requests", ["path", "status", "version"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["path", "version"])


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = route.path if route else "unmatched"
    REQUESTS.labels(path, str(response.status_code), APP_VERSION).inc()
    LATENCY.labels(path, APP_VERSION).observe(time.perf_counter() - start)
    return response


def inject_faults():
    if FAULT_LATENCY_MS:
        time.sleep(FAULT_LATENCY_MS / 1000)
    if random.random() < FAULT_ERROR_RATE:
        raise HTTPException(status_code=500, detail="injected fault")


@app.get("/products")
def products():
    inject_faults()
    try:
        resp = inventory.get("/items")
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="inventory unavailable") from exc
    data = resp.json()
    return {
        "version": APP_VERSION,
        "inventory_version": data["version"],
        "products": [
            {"name": name, "quantity": qty, "in_stock": qty > 0}
            for name, qty in data["items"].items()
        ],
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# Readiness deliberately does NOT check inventory: if inventory is down, every api pod
# would turn unready at once and the whole service would vanish (cascading failure).
@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/crash")
def crash():
    if not ALLOW_CRASH:
        raise HTTPException(status_code=404)
    os._exit(1)
