from typing import Literal

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .catalog import DB, require
from .inventory import apply_movement, lock_products
from .models import OrderLine, Product, PurchaseOrder, Supplier, Warehouse
from .schemas import MovementIn, OrderIn, OrderOut

router = APIRouter(prefix="/api/purchase-orders", tags=["Procurement"])


def validate_order(db, data):
    require(db, Supplier, data.supplier_id)
    require(db, Warehouse, data.warehouse_id)
    for item in data.items:
        product = require(db, Product, item.product_id)
        if product.supplier_id != data.supplier_id:
            raise HTTPException(422, "Every order line must belong to the selected supplier")


@router.get("", response_model=list[OrderOut])
def orders(db: DB):
    return db.scalars(select(PurchaseOrder).order_by(PurchaseOrder.id.desc()).limit(200)).all()


@router.get("/{record_id}", response_model=OrderOut)
def order(record_id: int, db: DB):
    return require(db, PurchaseOrder, record_id)


@router.post("", response_model=OrderOut, status_code=201)
def create_order(data: OrderIn, db: DB):
    validate_order(db, data)
    row = PurchaseOrder(**data.model_dump(exclude={"items"}), items=[OrderLine(**item.model_dump()) for item in data.items])
    db.add(row)
    db.commit()
    return row


@router.put("/{record_id}", response_model=OrderOut)
def edit_order(record_id: int, data: OrderIn, db: DB):
    row = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == record_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Purchase order not found")
    if row.status != "draft":
        raise HTTPException(409, "Only draft orders can be edited")
    validate_order(db, data)
    row.items.clear()
    db.flush()
    for key, value in data.model_dump(exclude={"items"}).items():
        setattr(row, key, value)
    row.items = [OrderLine(**item.model_dump()) for item in data.items]
    db.commit()
    return row


@router.post("/{record_id}/{action}", response_model=OrderOut)
def transition(record_id: int, action: Literal["order", "receive", "cancel"], db: DB):
    row = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == record_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Purchase order not found")
    target = {"order": "ordered", "receive": "received", "cancel": "cancelled"}[action]
    if row.status == target:
        return row
    allowed = {"order": {"draft"}, "receive": {"ordered"}, "cancel": {"draft", "ordered"}}
    if row.status not in allowed[action]:
        raise HTTPException(409, f"Cannot {action} an order that is {row.status}")
    if action == "receive":
        lock_products(db, [line.product_id for line in row.items])
        for line in sorted(row.items, key=lambda item: item.product_id):
            apply_movement(db, MovementIn(product_id=line.product_id, warehouse_id=row.warehouse_id,
                                         kind="receipt", quantity=line.quantity, reference=f"PO-{row.id:04}",
                                         idempotency_key=f"po-receive-{row.id}-{line.id}"))
    row.status = target
    db.commit()
    return row

