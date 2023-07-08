from lib.utils import try_get
from reqs import strike
from uuid import uuid4


def strike_invoice_id(prompter, prompt):
    invoice = strike(
        "POST",
        "invoices",
        {
            "correlationId": str(uuid4()),
            "description": f"ATL BitLab Bot: Payer - {prompter}, Prompt - {prompt}",
            "amount": {"amount": "1.00", "currency": "USD"},
        },
    )
    return try_get(invoice, "invoiceId")


def strike_quote(invoice_id):
    quote = strike("POST", f"invoices/{invoice_id}/quote")
    return (
        try_get(quote, "lnInvoice"),
        try_get(quote, "expirationInSec"),
    )
