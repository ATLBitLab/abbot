from lib.env import STRIKE_API_KEY
from lib.utils import try_get
from lib.api.reqs import http_request
STRIKE_BASE_URL = "https://api.strike.me/v1"
STRIKE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {STRIKE_API_KEY}",
}

class Strike:
    def __init__(self, correlation_id, description, invoice_id):
        self.correlation_id = correlation_id
        self.description = description
        self.invoice_id = invoice_id

    def invoice(self):
        response = http_request(
            "POST",
            f"{STRIKE_BASE_URL}/invoices",
            {
                "correlationId": self.correlation_id,
                "description": self.description,
                "amount": {"amount": "1.00", "currency": "USD"},
            },
        )
        self.invoice_id = try_get(response, "invoiceId")
        return False

    def quote(self):
        response = http_request("POST", f"invoices/{self.invoice_id}/quote")
        return (
            try_get(response, "lnInvoice"),
            try_get(response, "expirationInSec"),
        )

    def paid(self):
        check = http_request("GET", f"invoices/{self.invoice_id}")
        return try_get(check, "state") == "PAID"

    def expire_invoice(self):
        response = ("PATCH", f"invoices/${self.invoice_id}/cancel")
        return try_get(response, "state") == "CANCELLED"
