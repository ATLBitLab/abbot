from lib.env import STRIKE_API_KEY

STRIKE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {STRIKE_API_KEY}",
}
STRIKE_BASE_URL = "https://api.strike.me/v1"
STRIKE_INVOICES_URL = f"{STRIKE_BASE_URL}/invoices"
from lib.utils import try_get
from lib.api.reqs import http_request
import qrcode
from io import BytesIO


class Strike:
    def __init__(self, correlation_id, description):
        self.correlation_id = correlation_id
        self.description = description
        self.invoice_id = None

    def invoice(self):
        response = http_request(
            STRIKE_HEADERS,
            "POST",
            STRIKE_INVOICES_URL,
            {
                "correlationId": self.correlation_id,
                "description": self.description,
                "amount": {"amount": "1.00", "currency": "USD"},
            },
        )
        self.invoice_id = try_get(response, "invoiceId")
        response = http_request(
            STRIKE_HEADERS, "POST", f"{STRIKE_INVOICES_URL}/{self.invoice_id}/quote"
        )
        return (
            try_get(response, "lnInvoice"),
            try_get(response, "expirationInSec"),
        )

    def paid(self):
        response = http_request(
            STRIKE_HEADERS, "GET", f"{STRIKE_INVOICES_URL}/{self.invoice_id}"
        )
        return try_get(response, "state") == "PAID"

    def expire_invoice(self):
        response = http_request(
            STRIKE_HEADERS, "PATCH", f"{STRIKE_INVOICES_URL}/{self.invoice_id}/cancel"
        )
        return try_get(response, "state") == "CANCELLED"

    def qr_code(self, ln_invoice):
        qr = qrcode.make(ln_invoice)
        bio = BytesIO()
        qr.save(bio, "PNG")
        bio.seek(0)
        return bio
