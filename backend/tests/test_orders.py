def order_data(catalog):
    return {
        "supplier_id": catalog["supplier"]["id"],
        "warehouse_id": catalog["warehouses"][0]["id"],
        "items": [{"product_id": catalog["product"]["id"], "quantity": 15, "unit_cost_cents": 800}],
    }


def test_order_state_machine_and_duplicate_receipt(client, catalog):
    created = client.post("/api/purchase-orders", json=order_data(catalog))
    assert created.status_code == 201
    uri = f"/api/purchase-orders/{created.json()['id']}"
    assert client.post(uri + "/receive").status_code == 409
    assert client.put(uri, json=order_data(catalog) | {"note": "Express delivery"}).status_code == 200
    assert client.post(uri + "/order").json()["status"] == "ordered"
    assert client.put(uri, json=order_data(catalog)).status_code == 409
    assert client.post(uri + "/receive").json()["status"] == "received"
    assert client.post(uri + "/receive").status_code == 200
    assert client.post(uri + "/cancel").status_code == 409
    assert client.get("/api/inventory").json()[0]["on_hand"] == 15
    assert len(client.get("/api/movements").json()) == 1


def test_cancelled_order_does_not_receive(client, catalog):
    row = client.post("/api/purchase-orders", json=order_data(catalog)).json()
    uri = f"/api/purchase-orders/{row['id']}"
    assert client.post(uri + "/cancel").status_code == 200
    assert client.post(uri + "/order").status_code == 409
    assert client.post(uri + "/receive").status_code == 409
    assert client.get("/api/inventory").json() == []


def test_order_rejects_duplicate_lines_and_wrong_supplier(client, catalog):
    data = order_data(catalog)
    assert client.post("/api/purchase-orders", json=data | {"items": data["items"] * 2}).status_code == 422
    supplier = client.post("/api/suppliers", json={"name": "Different supplier"}).json()
    assert client.post("/api/purchase-orders", json=data | {"supplier_id": supplier["id"]}).status_code == 422
