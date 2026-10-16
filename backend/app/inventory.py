import hashlib
import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from .catalog import DB, require
from .models import Balance, Movement, Product, Reservation, Warehouse
from .schemas import MovementIn, MovementOut, ReservationIn, ReservationOut

router = APIRouter(prefix="/api", tags=["Inventory"])


def fingerprint(data):
    payload = data.model_dump(exclude={"idempotency_key"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def lock_products(db, product_ids):
    # Lock in a stable order to avoid deadlocks when two orders overlap.
    ids = sorted(set(product_ids))
    rows = db.scalars(select(Product).where(Product.id.in_(ids)).order_by(Product.id).with_for_update()).all()
    if len(rows) != len(ids):
        raise HTTPException(404, "Product not found")


def balance(db, product_id, warehouse_id):
    require(db, Warehouse, warehouse_id)
    row = db.scalar(
        select(Balance).where(Balance.product_id == product_id, Balance.warehouse_id == warehouse_id)
    )
    if row is None:
        row = Balance(product_id=product_id, warehouse_id=warehouse_id, on_hand=0, reserved=0)
        db.add(row)
        db.flush()
    return row


def duplicate(db, model, data):
    row = db.scalar(select(model).where(model.idempotency_key == data.idempotency_key))
    if row and row.fingerprint != fingerprint(data):
        raise HTTPException(409, "Idempotency key already belongs to a different request")
    return row


def apply_movement(db, data):
    existing = duplicate(db, Movement, data)
    if existing:
        return existing
    lock_products(db, [data.product_id])
    # A concurrent request may have committed while this transaction waited.
    existing = duplicate(db, Movement, data)
    if existing:
        return existing
    source = balance(db, data.product_id, data.warehouse_id)
    if data.kind == "receipt":
        source.on_hand += data.quantity
    else:
        if source.on_hand - source.reserved < data.quantity:
            raise HTTPException(409, "Insufficient available stock; reserved units cannot be moved")
        source.on_hand -= data.quantity
        if data.kind == "transfer":
            destination = balance(db, data.product_id, data.destination_id)
            destination.on_hand += data.quantity
    row = Movement(**data.model_dump(), fingerprint=fingerprint(data))
    db.add(row)
    db.flush()
    return row


@router.get("/inventory")
def inventory(db: DB):
    rows = db.execute(
        select(Balance, Product, Warehouse)
        .join(Product, Product.id == Balance.product_id)
        .join(Warehouse, Warehouse.id == Balance.warehouse_id)
        .order_by(Product.name, Warehouse.code)
    ).all()
    return [
        {
            "product_id": p.id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "price_cents": p.price_cents,
            "warehouse_id": w.id,
            "warehouse": w.name,
            "warehouse_code": w.code,
            "on_hand": b.on_hand,
            "reserved": b.reserved,
            "available": b.on_hand - b.reserved,
            "reorder_point": p.reorder_point,
        }
        for b, p, w in rows
    ]


@router.get("/movements", response_model=list[MovementOut])
def movements(db: DB, limit: int = Query(50, ge=1, le=200)):
    return db.scalars(select(Movement).order_by(Movement.id.desc()).limit(limit)).all()


@router.post("/movements", response_model=MovementOut, status_code=201)
def create_movement(data: MovementIn, db: DB):
    if data.idempotency_key.startswith(("reservation-fulfill-", "po-receive-")):
        raise HTTPException(422, "Idempotency key prefix is reserved for internal stock operations")
    row = apply_movement(db, data)
    db.commit()
    return row


@router.get("/reservations", response_model=list[ReservationOut])
def reservations(db: DB):
    return db.scalars(select(Reservation).order_by(Reservation.id.desc()).limit(200)).all()


@router.post("/reservations", response_model=ReservationOut, status_code=201)
def reserve(data: ReservationIn, db: DB):
    lock_products(db, [data.product_id])
    existing = duplicate(db, Reservation, data)
    if existing:
        return existing
    stock = balance(db, data.product_id, data.warehouse_id)
    if stock.on_hand - stock.reserved < data.quantity:
        raise HTTPException(409, "Insufficient available stock")
    stock.reserved += data.quantity
    row = Reservation(**data.model_dump(), fingerprint=fingerprint(data))
    db.add(row)
    db.commit()
    return row


@router.post("/reservations/{record_id}/{action}", response_model=ReservationOut)
def finish_reservation(record_id: int, action: Literal["release", "fulfill"], db: DB):
    row = db.scalar(select(Reservation).where(Reservation.id == record_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Reservation not found")
    target = {"release": "released", "fulfill": "fulfilled"}[action]
    if row.status == target:
        return row
    if row.status != "active":
        raise HTTPException(409, "Reservation has already been closed")
    lock_products(db, [row.product_id])
    stock = balance(db, row.product_id, row.warehouse_id)
    stock.reserved -= row.quantity
    if action == "fulfill":
        apply_movement(
            db,
            MovementIn(
                product_id=row.product_id,
                warehouse_id=row.warehouse_id,
                kind="issue",
                quantity=row.quantity,
                reference=row.reference,
                idempotency_key=f"reservation-fulfill-{row.id}",
            ),
        )
    row.status = target
    db.commit()
    return row
