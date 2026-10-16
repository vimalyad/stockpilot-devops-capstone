from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Name = Annotated[str, Field(min_length=1, max_length=120)]
Positive = Annotated[int, Field(gt=0, le=1_000_000)]
Nonnegative = Annotated[int, Field(ge=0, le=100_000_000)]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True, extra="forbid")


class SupplierIn(Schema):
    name: Name
    email: str = Field(default="", max_length=200)
    lead_days: int = Field(default=3, ge=0, le=365)


class SupplierOut(SupplierIn):
    id: int


class ProductIn(Schema):
    sku: str = Field(pattern=r"^[A-Z0-9][A-Z0-9-]{1,31}$")
    name: Name
    category: str = Field(default="General", min_length=1, max_length=60)
    price_cents: Nonnegative = 0
    reorder_point: Nonnegative = 10
    supplier_id: Positive | None = None


class ProductOut(ProductIn):
    id: int


class WarehouseIn(Schema):
    code: str = Field(pattern=r"^[A-Z0-9][A-Z0-9-]{1,15}$")
    name: Name
    location: Name


class WarehouseOut(WarehouseIn):
    id: int


class MovementIn(Schema):
    product_id: Positive
    warehouse_id: Positive
    kind: Literal["receipt", "issue", "transfer"]
    destination_id: Positive | None = None
    quantity: Positive
    reference: str = Field(default="", max_length=120)
    idempotency_key: str = Field(min_length=8, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")

    @model_validator(mode="after")
    def valid_destination(self):
        if self.kind == "transfer":
            if self.destination_id is None or self.destination_id == self.warehouse_id:
                raise ValueError("Transfers require a different destination warehouse")
        elif self.destination_id is not None:
            raise ValueError("Only transfers accept a destination")
        return self


class MovementOut(MovementIn):
    id: int
    created_at: datetime


class ReservationIn(Schema):
    product_id: Positive
    warehouse_id: Positive
    quantity: Positive
    reference: Name
    idempotency_key: str = Field(min_length=8, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")


class ReservationOut(ReservationIn):
    id: int
    status: str
    created_at: datetime


class OrderLineIn(Schema):
    product_id: Positive
    quantity: Positive
    unit_cost_cents: Nonnegative


class OrderIn(Schema):
    supplier_id: Positive
    warehouse_id: Positive
    note: str = Field(default="", max_length=250)
    items: list[OrderLineIn] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def unique_products(self):
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("Each product may appear only once per order")
        return self


class OrderOut(OrderIn):
    id: int
    status: str
    created_at: datetime

