from uuid import uuid4
from qrcode import make
from io import BytesIO

from lib.utils import http_request
from lib.env import STRIKE_API_KEY

STRIKE_BASE_URL = "https://api.strike.me/v1"
STRIKE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {STRIKE_API_KEY}",
}

def do_strike_logic(method, url, path, json=None, headers=STRIKE_HEADERS):
    try:
        response = http_request(
            "POST",
            "invoices",
            {
                "correlationId": str(uuid4()),
                "description": f"ATL BitLab Bot Prompt: {prompt}",
                "amount": {"amount": "1.00", "currency": "USD"},
            },
        )
        invoice = response.json()
        invoice_id = invoice.get("invoiceId")

        response = http_request("POST", f"invoices/{invoice_id}/quote")
        quote = response.json()
        ln_invoice = quote.get("lnInvoice")
        qr = make(ln_invoice)
        bio = BytesIO()
        qr.save(bio, "PNG")
        bio.seek(0)
    except Exception as e:
        print(e)


"""
await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=bio,
            caption=f'To get the response to your prompt: "{prompt}"\nPlease pay the invoice:\n{ln_invoice}',
        )
"""