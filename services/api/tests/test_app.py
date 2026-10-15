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
