import pytest


def test_health_without_database(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_documentation_and_metrics(client):
    assert client.get("/docs").status_code == 200
    assert "/api/products" in client.get("/openapi.json").json()["paths"]
    client.get("/health")
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert 'stockpilot_http_requests_total{method="GET",route="/health",status="200"}' in metrics.text


def test_product_crud(client):
    data = {"sku": "DEMO-01", "name": "Cable", "price_cents": 500}
    response = client.post("/api/products", json=data)
    assert response.status_code == 201
    uri = response.headers["location"]
    assert client.get(uri).json()["name"] == "Cable"
    assert client.put(uri, json=data | {"name": "Braided cable"}).json()["name"] == "Braided cable"
    assert client.get("/api/products?search=braided").json()[0]["sku"] == "DEMO-01"
    assert client.delete(uri).status_code == 204
    assert client.get(uri).status_code == 404


@pytest.mark.parametrize(
    "change",
    [{"name": " "}, {"price_cents": -1}, {"sku": "invalid sku"}, {"reorder_point": -1}, {"unexpected": True}],
)
def test_invalid_product_rejected(client, change):
    assert (
        client.post("/api/products", json={"sku": "VALID-01", "name": "Product"} | change).status_code == 422
    )


def test_duplicate_sku_conflict(client):
    data = {"sku": "UNIQUE-01", "name": "Product"}
    assert client.post("/api/products", json=data).status_code == 201
    response = client.post("/api/products", json=data)
    assert response.status_code == 409
    assert "SQL" not in response.text


def test_supplier_reference_and_missing_product(client, catalog):
    assert client.delete(f"/api/suppliers/{catalog['supplier']['id']}").status_code == 409
    assert client.get("/api/products/9999").status_code == 404


def test_product_supplier_must_exist(client):
    assert (
        client.post(
            "/api/products", json={"sku": "ORPHAN-01", "name": "Product", "supplier_id": 99999}
        ).status_code
        == 404
    )


def test_suppliers_crud(client):
    created = client.post("/api/suppliers", json={"name": "Independent supplier"})
    uri = f"/api/suppliers/{created.json()['id']}"
    assert created.status_code == 201
    assert client.put(uri, json={"name": "Updated supplier", "lead_days": 4}).status_code == 200
    assert client.get("/api/suppliers").json()[0]["lead_days"] == 4
    assert client.delete(uri).status_code == 204


def test_search_does_not_treat_percent_as_wildcard(client, catalog):
    assert client.get("/api/products", params={"search": "%"}).json() == []
