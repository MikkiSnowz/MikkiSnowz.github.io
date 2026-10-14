import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def table_order_url(frontend_url: str, qr_token: str) -> str:
    return f"{frontend_url.rstrip('/')}/t/{qr_token}"


def takeaway_order_url(frontend_url: str) -> str:
    return f"{frontend_url.rstrip('/')}/takeaway"


def qr_png(data: str, box_size: int = 10) -> bytes:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=box_size, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return buf.getvalue()
