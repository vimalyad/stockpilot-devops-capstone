from sqlalchemy import func, select

from .models import Balance, Movement, Product, PurchaseOrder, Warehouse


def snapshot(db):
    totals = (
        select(
            Balance.product_id,
            func.sum(Balance.on_hand).label("on_hand"),
            func.sum(Balance.reserved).label("reserved"),
        )
        .group_by(Balance.product_id)
        .subquery()
    )
    rows = db.execute(
        select(Product, func.coalesce(totals.c.on_hand, 0), func.coalesce(totals.c.reserved, 0))
        .outerjoin(totals, Product.id == totals.c.product_id)
        .order_by(Product.name)
    ).all()
    low = [
        {
            "product_id": p.id,
            "sku": p.sku,
            "name": p.name,
            "available": hand - reserved,
            "reorder_point": p.reorder_point,
            "recommended_quantity": min(1_000_000, max(p.reorder_point * 2 - hand + reserved, 1)),
            "supplier_id": p.supplier_id,
        }
        for p, hand, reserved in rows
        if hand - reserved <= p.reorder_point
    ]
    warehouses = db.execute(
        select(Warehouse.name, func.coalesce(func.sum(Balance.on_hand), 0))
        .outerjoin(Balance)
        .group_by(Warehouse.id, Warehouse.name)
        .order_by(Warehouse.id)
    ).all()
    recent = db.scalars(select(Movement).order_by(Movement.id.desc()).limit(8)).all()
    categories = {}
    for p, hand, reserved in rows:
        categories[p.category] = categories.get(p.category, 0) + hand
    return {
        "product_count": len(rows),
        "on_hand": sum(h for _, h, _ in rows),
        "reserved": sum(r for _, _, r in rows),
        "available": sum(h - r for _, h, r in rows),
        "inventory_value_cents": sum(p.price_cents * h for p, h, _ in rows),
        "open_orders": db.scalar(
            select(func.count())
            .select_from(PurchaseOrder)
            .where(PurchaseOrder.status.in_(["draft", "ordered"]))
        ),
        "low_stock": low,
        "warehouses": [{"name": name, "units": units} for name, units in warehouses],
        "categories": [{"name": name, "units": units} for name, units in sorted(categories.items())],
        "recent_movements": [
            {
                "id": m.id,
                "product_id": m.product_id,
                "kind": m.kind,
                "quantity": m.quantity,
                "reference": m.reference,
                "created_at": m.created_at.isoformat(),
            }
            for m in recent
        ],
    }
