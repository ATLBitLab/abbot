from typing import Dict
import httpx
from httpx import Response
from abc import ABC, abstractmethod
from lib.utils import success, try_get
from lib.logger import bot_debug


def init_payment_processor():
    PAYMENT_PROCESSOR_KIND = "strike"
    PAYMENT_PROCESSOR_TOKEN = "A50FA9B3130792435D5EDD067AFAD10B345F84F7927A734C92BBC3F933205B37"
    LNBITS_BASE_URL = "LNBITS_BASE_URL"
    available_processors = ["strike", "lnbits", "opennode"]
    if PAYMENT_PROCESSOR_KIND is None or PAYMENT_PROCESSOR_KIND not in available_processors:
        raise Exception(f"PAYMENT_PROCESSOR_KIND must be one of {', '.join(available_processors)}")
    if not PAYMENT_PROCESSOR_TOKEN.strip():
        raise Exception("PAYMENT_PROCESSOR_TOKEN must be a valid API token")
    if PAYMENT_PROCESSOR_KIND == "strike":
        return Strike(PAYMENT_PROCESSOR_TOKEN)
    elif PAYMENT_PROCESSOR_KIND == "lnbits":
        return LNbits(LNBITS_BASE_URL, PAYMENT_PROCESSOR_TOKEN)
    elif PAYMENT_PROCESSOR_KIND == "opennode":
        return OpenNode(PAYMENT_PROCESSOR_TOKEN)


class Processor(ABC):
    """
    An abstract class that all payment processors should implement.
    """

    @abstractmethod
    def get_invoice(self, correlation_id, description):
        pass

    @abstractmethod
    def invoice_is_paid(self, invoice_id):
        pass

    @abstractmethod
    def expire_invoice(self, invoice_id):
        pass


class Strike(Processor):
    """
    A Strike payment processor
    """

    CHAT_ID_INVOICE_ID_MAP = {}

    def __init__(self, api_key):
        super().__init__()
        assert api_key is not None, "a Strike API key must be supplied"
        self._client = httpx.AsyncClient(
            base_url="https://api.strike.me/v1",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

    async def get_invoice(self, correlation_id, description, amount, chat_id):
        invoice_resp: Response = await self._client.post(
            "/invoices",
            json={
                "correlationId": correlation_id,
                "description": description,
                "amount": {"amount": amount, "currency": "USD"},
            },
        )
        invoice_data: Dict = invoice_resp.json()
        bot_debug.log(__name__, f"strike => get_invoice => invoice_resp={invoice_resp.text}")

        invoice_id = try_get(invoice_data, "invoiceId")
        self.CHAT_ID_INVOICE_ID_MAP[chat_id] = invoice_id
        bot_debug.log(__name__, f"strike => get_invoice => invoice_id={invoice_id}")

        quote_resp = await self._client.post(f"/invoices/{invoice_id}/quote")
        bot_debug.log(__name__, f"strike => get_invoice => quote_resp={quote_resp.text}")

        quote_data: Dict = quote_resp.json()
        bot_debug.log(__name__, f"strike => get_invoice => quote_data={quote_data}")

        return success(
            message="Invoice created",
            invoice_id=invoice_id,
            lnInvoice=try_get(quote_data, "lnInvoice"),
            expirationInSec=try_get(quote_data, "expirationInSec"),
        )

    async def invoice_is_paid(self, invoice_id):
        resp: Response = await self._client.get(f"/invoices/{invoice_id}")
        resp_data: Dict = resp.json()
        return try_get(resp_data, "state") == "PAID"

    async def expire_invoice(self, invoice_id):
        resp: Response = await self._client.patch(f"/invoices/{invoice_id}/cancel")
        resp_data: Dict = resp.json()
        return try_get(resp_data, "state") == "CANCELLED"


class LNbits(Processor):
    """
    An LNbits payment processor
    """

    def __init__(self, base_url, api_key):
        super().__init__()
        assert base_url is not None, "an LNbits base URL must be supplied"
        assert api_key is not None, "an LNbits API key must be supplied"
        self._client = httpx.AsyncClient(
            base_url=f"{base_url}/api/v1",
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": api_key,
            },
        )

    async def get_invoice(self, correlation_id, description):
        create_resp = await self._client.post(
            "/payments",
            json={
                "out": False,
                "amount": 1,
                "unit": "USD",
                "unhashed_description": description.encode("utf-8").hex(),
                "extra": {
                    "correlationId": correlation_id,
                },
            },
        )
        payment_request = try_get(create_resp, "payment_request")
        payment_hash = try_get(create_resp, "payment_hash")
        payment_resp = await self._client.get(f"/payments/{payment_hash}")

        return (
            payment_hash,
            payment_request,
            int(try_get(payment_resp, "details", "expiry")),
        )

    async def invoice_is_paid(self, payment_hash):
        resp = await self._client.get(f"/payments/{payment_hash}")
        return try_get(resp, "paid")

    async def expire_invoice(self, invoice_id):
        """LNbits doesn't seem to have an explicit way to expire an invoice"""
        pass


class OpenNode(Processor):
    """
    An OpenNode payment processor
    """

    def __init__(self, api_key):
        super().__init__()
        assert api_key is not None, "an OpenNode API key with invoice permissions must be supplied"
        self._client = httpx.AsyncClient(
            base_url="https://api.opennode.com",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": api_key,
            },
        )

    async def get_invoice(self, correlation_id, description):
        resp = await self._client.post(
            "/v1/charges",
            json={
                "amount": 1,
                "currency": "USD",
                "order_id": correlation_id,
                "description": description,
            },
        )

        return (
            try_get(resp, "data", "id"),
            try_get(resp, "data", "lightning_invoice", "payreq"),
            try_get(resp, "data", "ttl"),
        )

    async def invoice_is_paid(self, invoice_id):
        resp = await self._client.get(f"/v2/charge/{invoice_id}")
        return try_get(resp, "data", "status") == "paid"

    async def expire_invoice(self, invoice_id):
        """OpenNode doesn't seem to have an explicit way to expire an invoice"""
        pass
