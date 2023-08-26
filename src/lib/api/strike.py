from lib.utils import try_get, http_request
import qrcode
from io import BytesIO


class API:
    BASE_URL = "https://api.strike.me/v1"
    INVOICES_URL = f"{BASE_URL}/invoices"
    HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


class Strike(API):
    def __init__(self, api_key, correlation_id, description):
        assert (api_key is not None, "Strike API key must be supplied")
        self.api_key = api_key
        self.correlation_id = correlation_id
        self.description = description
        self.invoice_id = None
        self.STRIKE_HEADERS = {
            "Authorization": f"Bearer {self.api_key}",
            **Strike.HEADERS,
        }

    def invoice(self):
        response = http_request(
            self.STRIKE_HEADERS,
            "POST",
            Strike.INVOICES_URL,
            {
                "correlationId": self.correlation_id,
                "description": self.description,
                "amount": {"amount": "1.00", "currency": "USD"},
            },
        )
        self.invoice_id = try_get(response, "invoiceId")
        response = http_request(
            self.STRIKE_HEADERS,
            "POST",
            f"{Strike.INVOICES_URL}/{self.invoice_id}/quote",
        )
        return (
            try_get(response, "lnInvoice"),
            try_get(response, "expirationInSec"),
        )

    def paid(self):
        response = http_request(
            self.STRIKE_HEADERS, "GET", f"{Strike.INVOICES_URL}/{self.invoice_id}"
        )
        return try_get(response, "state") == "PAID"

    def expire_invoice(self):
        response = http_request(
            self.STRIKE_HEADERS,
            "PATCH",
            f"{Strike.INVOICES_URL}/{self.invoice_id}/cancel",
        )
        return try_get(response, "state") == "CANCELLED"

    def qr_code(self, ln_invoice):
        qr = qrcode.make(ln_invoice)
        bio = BytesIO()
        qr.save(bio, "PNG")
        bio.seek(0)
        return bio
