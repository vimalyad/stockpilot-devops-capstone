from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Product, Supplier, Warehouse
from .schemas import ProductIn, ProductOut, SupplierIn, SupplierOut, WarehouseIn, WarehouseOut

router = APIRouter(prefix="/api", tags=["Catalog"])
DB = Annotated[Session, Depends(get_db)]


def require(db, model, record_id):
    row = db.get(model, record_id)
    if row is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return row


@router.get("/products", response_model=list[ProductOut])
def products(
    db: DB,
    search: str = Query("", max_length=120),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(Product).order_by(Product.id)
    if search:
        query = query.where(
            Product.name.icontains(search, autoescape=True) | Product.sku.icontains(search, autoescape=True)
        )
    return db.scalars(query.offset(offset).limit(limit)).all()


@router.get("/products/{record_id}", response_model=ProductOut)
def product(record_id: int, db: DB):
    return require(db, Product, record_id)


@router.post("/products", status_code=201, response_model=ProductOut)
def create_product(data: ProductIn, db: DB, response: Response):
    if data.supplier_id:
        require(db, Supplier, data.supplier_id)
    row = Product(**data.model_dump())
    db.add(row)
    db.commit()
    response.headers["Location"] = f"/api/products/{row.id}"
    return row


@router.put("/products/{record_id}", response_model=ProductOut)
def update_product(record_id: int, data: ProductIn, db: DB):
    row = require(db, Product, record_id)
    if data.supplier_id:
        require(db, Supplier, data.supplier_id)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return row


@router.delete("/products/{record_id}", status_code=204)
def delete_product(record_id: int, db: DB):
    db.delete(require(db, Product, record_id))
    db.commit()


@router.get("/suppliers", response_model=list[SupplierOut])
def suppliers(db: DB):
    return db.scalars(select(Supplier).order_by(Supplier.name).limit(200)).all()


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierIn, db: DB):
    row = Supplier(**data.model_dump())
    db.add(row)
    db.commit()
    return row


@router.put("/suppliers/{record_id}", response_model=SupplierOut)
def update_supplier(record_id: int, data: SupplierIn, db: DB):
    row = require(db, Supplier, record_id)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return row


@router.delete("/suppliers/{record_id}", status_code=204)
def delete_supplier(record_id: int, db: DB):
    db.delete(require(db, Supplier, record_id))
    db.commit()


@router.get("/warehouses", response_model=list[WarehouseOut])
def warehouses(db: DB):
    return db.scalars(select(Warehouse).order_by(Warehouse.id).limit(200)).all()


@router.post("/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(data: WarehouseIn, db: DB):
    row = Warehouse(**data.model_dump())
    db.add(row)
    db.commit()
    return row
