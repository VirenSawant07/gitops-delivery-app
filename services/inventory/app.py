import json
import os
import random
import socket
import time
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# Settings come from environment variables, so Kubernetes can change them without code changes
APP_VERSION = os.getenv("APP_VERSION", "dev")
FAULT_ERROR_RATE = float(os.getenv("FAULT_ERROR_RATE", "0"))  # 0.3 = fail 30% of requests
FAULT_LATENCY_MS = int(os.getenv("FAULT_LATENCY_MS", "0"))  # extra delay per request
ALLOW_CRASH = os.getenv("ALLOW_CRASH") == "true"
POD_NAME = socket.gethostname()  # in Kubernetes the hostname is the pod name

app = FastAPI(title="inventory")

STOCK = {"pen": 10, "notebook": 0, "bag": 4, "pencil": 25, "highlighter": 3, "sticky notes": 12}

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
    duration = time.perf_counter() - start
    LATENCY.labels(path, APP_VERSION).observe(duration)
    log_request(request, response.status_code, duration)
    return response


def log_request(request: Request, status: int, duration: float):
    # One JSON line per request on stdout: easy to filter with jq or load into a log stack.
    # Replaces uvicorn's plain-text access log (turned off with --no-access-log in the Dockerfile).
    entry = {
        "time": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "level": "error" if status >= 500 else "info",
        "method": request.method,
        "path": request.url.path,
        "status": status,
        "duration_ms": round(duration * 1000, 1),
        "version": APP_VERSION,
        "pod": POD_NAME,
    }
    print(json.dumps(entry), flush=True)


def inject_faults():
    if FAULT_LATENCY_MS:
        time.sleep(FAULT_LATENCY_MS / 1000)
    if random.random() < FAULT_ERROR_RATE:
        raise HTTPException(status_code=500, detail="injected fault")


@app.get("/items")
def items():
    inject_faults()
    return {"version": APP_VERSION, "items": STOCK}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


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
