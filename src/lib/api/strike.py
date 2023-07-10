from lib.utils import try_get
from reqs import strike


class Strike:
    def __init__(self, correlation_id, description, invoice_id):
        self.correlation_id = correlation_id
        self.description = description
        self.invoice_id = invoice_id

    def invoice(self):
        response = strike(
            "POST",
            "invoices",
            {
                "correlationId": self.correlation_id,
                "description": self.description,
                "amount": {"amount": "1.00", "currency": "USD"},
            },
        )
        self.invoice_id = try_get(response, "invoiceId")
        return self.invoice_id, False

    def quote(self):
        response = strike("POST", f"invoices/{self.invoice_id}/quote")
        return (
            try_get(response, "lnInvoice"),
            try_get(response, "expirationInSec"),
        )

    def paid(self):
        check = strike("GET", f"invoices/{self.invoice_id}")
        return try_get(check, "state") == "PAID"

    def expire_invoice(self):
        response = ("PATCH", f"invoices/${self.invoice_id}/cancel")
        return try_get(response, "state") == "PAID"
