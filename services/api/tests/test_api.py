import json

import httpx
from fastapi.testclient import TestClient

import app as api_app

client = TestClient(api_app.app)


def fake_inventory(handler, monkeypatch):
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        api_app, "inventory", httpx.Client(transport=transport, base_url="http://inv")
    )


def test_products_merges_inventory_stock(monkeypatch):
    fake_inventory(
        lambda req: httpx.Response(200, json={"version": "v2", "items": {"pen": 3, "bag": 0}}),
        monkeypatch,
    )
    resp = client.get("/products")
    assert resp.status_code == 200
    assert resp.json() == {
        "version": "dev",
        "inventory_version": "v2",
        "environment": "local",
        "served_by": api_app.POD_NAME,
        "products": [
            {"name": "pen", "quantity": 3, "in_stock": True},
            {"name": "bag", "quantity": 0, "in_stock": False},
        ],
    }


def test_inventory_down_returns_502(monkeypatch):
    def refuse(req):
        raise httpx.ConnectError("connection refused")

    fake_inventory(refuse, monkeypatch)
    assert client.get("/products").status_code == 502


def test_inventory_error_returns_502(monkeypatch):
    fake_inventory(lambda req: httpx.Response(500), monkeypatch)
    assert client.get("/products").status_code == 502


def test_ready_does_not_depend_on_inventory(monkeypatch):
    def refuse(req):
        raise httpx.ConnectError("connection refused")

    fake_inventory(refuse, monkeypatch)
    assert client.get("/readyz").status_code == 200


def test_fault_injection_returns_500(monkeypatch):
    monkeypatch.setattr(api_app, "FAULT_ERROR_RATE", 1.0)
    assert client.get("/products").status_code == 500


def test_shop_page_is_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Inkling" in resp.text
    assert resp.headers["Cache-Control"] == "no-cache"


def test_every_response_says_which_pod_served_it(monkeypatch):
    monkeypatch.setattr(api_app, "FAULT_ERROR_RATE", 1.0)
    resp = client.get("/products")
    assert resp.status_code == 500
    assert resp.headers["X-Served-By"] == api_app.POD_NAME


def test_each_request_logs_one_json_line(monkeypatch, capsys):
    monkeypatch.setattr(api_app, "FAULT_ERROR_RATE", 1.0)
    client.get("/products")
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert set(entry) == {
        "time",
        "level",
        "method",
        "path",
        "status",
        "duration_ms",
        "version",
        "pod",
    }
    assert entry["method"] == "GET"
    assert entry["path"] == "/products"
    assert entry["status"] == 500
    assert entry["level"] == "error"
    assert entry["pod"] == api_app.POD_NAME
