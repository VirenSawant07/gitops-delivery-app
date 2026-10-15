from fastapi.testclient import TestClient

import app as inventory_app

client = TestClient(inventory_app.app)


def test_items_returns_stock_and_version():
    resp = client.get("/items")
    assert resp.status_code == 200
    assert resp.json() == {"version": "dev", "items": {"pen": 10, "notebook": 0, "bag": 4}}


def test_health_and_ready():
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}


def test_metrics_count_requests_by_route():
    client.get("/items")
    body = client.get("/metrics").text
    assert 'http_requests_total{path="/items",status="200",version="dev"}' in body


def test_fault_injection_returns_500(monkeypatch):
    monkeypatch.setattr(inventory_app, "FAULT_ERROR_RATE", 1.0)
    assert client.get("/items").status_code == 500


def test_crash_is_disabled_by_default():
    assert client.post("/crash").status_code == 404
