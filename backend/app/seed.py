"""Idempotent, explicit demo seed. Never called automatically in production."""
from sqlalchemy import select

from .database import SessionLocal
from .inventory import apply_movement
from .models import Product, Supplier, Warehouse
from .schemas import MovementIn


def seed():
    with SessionLocal() as db:
        if db.scalar(select(Product.id).limit(1)):
            print("Catalog already populated; demo seed skipped")
            return
        suppliers = [Supplier(name="Circuit Supply Co.", email="orders@circuit.example", lead_days=3),
                     Supplier(name="Form & Function", email="dispatch@form.example", lead_days=5)]
        db.add_all(suppliers)
        warehouses = [Warehouse(code="DEL-01", name="Delhi distribution", location="New Delhi"),
                      Warehouse(code="BLR-02", name="Bengaluru fulfilment", location="Bengaluru")]
        db.add_all(warehouses)
        db.flush()
        items = [
            ("KB-104", "Mechanical keyboard", "Peripherals", 649900, 20, 0, 128, 64),
            ("MS-220", "Wireless precision mouse", "Peripherals", 249900, 30, 0, 18, 6),
            ("DS-050", "Aluminium laptop stand", "Workspace", 329900, 15, 1, 85, 42),
            ("CB-310", "USB-C braided cable", "Accessories", 79900, 50, 0, 220, 145),
            ("HB-007", "Seven-port USB hub", "Accessories", 449900, 25, 0, 12, 8),
            ("LT-012", "Adjustable desk light", "Workspace", 289900, 20, 1, 75, 30),
            ("PD-900", "Felt desk mat", "Workspace", 129900, 35, 1, 16, 10),
            ("AU-045", "Studio headphones", "Audio", 899900, 10, 0, 48, 24),
        ]
        for sku, name, category, price, reorder, supplier, first, second in items:
            product = Product(sku=sku, name=name, category=category, price_cents=price,
                              reorder_point=reorder, supplier_id=suppliers[supplier].id)
            db.add(product)
            db.flush()
            for warehouse, quantity in zip(warehouses, (first, second)):
                apply_movement(db, MovementIn(product_id=product.id, warehouse_id=warehouse.id, kind="receipt",
                                             quantity=quantity, reference="Opening demo inventory",
                                             idempotency_key=f"seed-{sku}-{warehouse.code}"))
        db.commit()
        print("Seeded 8 products, 2 suppliers, 2 warehouses and 16 opening receipts")


if __name__ == "__main__":
    seed()

