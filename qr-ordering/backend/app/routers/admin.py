"""Staff endpoints. Every request needs the X-Admin-Key header."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..integrations import dispatch_order
from ..models import DiningTable, MenuItem, Order, OrderStatus
from ..qr import qr_png, table_order_url, takeaway_order_url
from ..schemas import StaffOrderOut, StatusUpdateIn, TableAdminOut, TableCreateIn


def require_admin(
    x_admin_key: str | None = Header(default=None), settings: Settings = Depends(get_settings)
) -> None:
    if not settings.admin_api_key or not x_admin_key:
        raise HTTPException(401, "Missing admin key")
    if not hmac.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(401, "Invalid admin key")


router = APIRouter(prefix="/api/admin", tags=["staff"], dependencies=[Depends(require_admin)])

ACTIVE_STATUSES = [OrderStatus.placed, OrderStatus.preparing, OrderStatus.ready]


def get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Order not found")
    return order


# ---------- Orders ----------


@router.get("/orders", response_model=list[StaffOrderOut])
def list_orders(
    status: list[OrderStatus] | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    """Defaults to the orders the kitchen is working on, oldest first."""
    statuses = status or ACTIVE_STATUSES
    return db.scalars(
        select(Order).where(Order.status.in_(statuses)).order_by(Order.created_at).limit(limit)
    ).all()


@router.patch("/orders/{order_id}/status", response_model=StaffOrderOut)
def update_status(order_id: int, data: StatusUpdateIn, db: Session = Depends(get_db)):
    order = get_order_or_404(db, order_id)
    order.status = data.status
    db.commit()
    return order


@router.post("/orders/{order_id}/dispatch", response_model=StaffOrderOut)
def retry_dispatch(
    order_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    """Re-send an order to the downstream system (e.g. after the POS was offline)."""
    order = get_order_or_404(db, order_id)
    if order.status in (OrderStatus.awaiting_payment, OrderStatus.cancelled):
        raise HTTPException(409, "Only confirmed orders can be sent")
    dispatch_order(db, order, settings)
    return order


# ---------- Menu ----------


class AvailabilityIn(BaseModel):
    is_available: bool


@router.patch("/menu-items/{item_id}")
def set_item_availability(item_id: int, data: AvailabilityIn, db: Session = Depends(get_db)):
    """Mark an item sold out (or back in stock)."""
    item = db.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(404, "Menu item not found")
    item.is_available = data.is_available
    db.commit()
    return {"id": item.id, "is_available": item.is_available}


# ---------- Tables & QR codes ----------


def table_admin_out(table: DiningTable, settings: Settings) -> TableAdminOut:
    return TableAdminOut(
        id=table.id,
        name=table.name,
        qr_token=table.qr_token,
        is_active=table.is_active,
        order_url=table_order_url(settings.frontend_url, table.qr_token),
        qr_png_url=f"/api/admin/tables/{table.id}/qr.png",
    )


@router.get("/tables", response_model=list[TableAdminOut])
def list_tables(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    tables = db.scalars(select(DiningTable).order_by(DiningTable.id)).all()
    return [table_admin_out(t, settings) for t in tables]


@router.post("/tables", response_model=TableAdminOut, status_code=201)
def create_table(
    data: TableCreateIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    table = DiningTable(name=data.name)
    db.add(table)
    db.commit()
    return table_admin_out(table, settings)


@router.get("/tables/{table_id}/qr.png")
def table_qr(table_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    table = db.get(DiningTable, table_id)
    if table is None:
        raise HTTPException(404, "Table not found")
    return Response(qr_png(table_order_url(settings.frontend_url, table.qr_token)), media_type="image/png")


@router.get("/takeaway-qr.png")
def takeaway_qr(settings: Settings = Depends(get_settings)):
    """QR code for the counter/window: takeaway orders with no table."""
    return Response(qr_png(takeaway_order_url(settings.frontend_url)), media_type="image/png")
