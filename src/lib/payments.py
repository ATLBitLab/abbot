from typing import Dict
from abc import ABC, abstractmethod

import time
import httpx
from httpx import Response
from pymongo.results import InsertOneResult

from lib.db.mongo import mongo_abbot
from lib.logger import debug_bot, error_bot
from lib.db.utils import successful_insert_one
from lib.abbot.env import PAYMENT_PROCESSOR_KIND, PRICE_PROVIDER_KIND, LNBITS_BASE_URL
from lib.utils import error, success, successful_response, try_get

FILE_NAME = __name__


class PaymentProcessor(ABC):
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


class Strike(PaymentProcessor):
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

    def to_dict(self):
        return vars(self)

    async def get_invoice(self, correlation_id, description, amount, chat_id):
        log_name: str = f"{FILE_NAME}: Strike.get_invoice()"
        invoice_resp: Response = await self._client.post(
            "/invoices",
            json={
                "correlationId": correlation_id,
                "description": description,
                "amount": {"amount": amount, "currency": "USD"},
            },
        )
        invoice_data: Dict = invoice_resp.json()
        debug_bot.log(log_name, f"strike => get_invoice => invoice_resp={invoice_resp.text}")

        invoice_id = try_get(invoice_data, "invoiceId")
        self.CHAT_ID_INVOICE_ID_MAP[chat_id] = invoice_id
        debug_bot.log(log_name, f"strike => get_invoice => invoice_id={invoice_id}")

        quote_resp = await self._client.post(f"/invoices/{invoice_id}/quote")
        debug_bot.log(log_name, f"strike => get_invoice => quote_resp={quote_resp.text}")

        quote_data: Dict = quote_resp.json()
        debug_bot.log(log_name, f"strike => get_invoice => quote_data={quote_data}")

        return success(
            "Invoice created",
            invoice_id=invoice_id,
            ln_invoice=try_get(quote_data, "lnInvoice"),
            expiration_in_sec=try_get(quote_data, "expirationInSec"),
        )

    async def invoice_is_paid(self, invoice_id):
        resp: Response = await self._client.get(f"/invoices/{invoice_id}")
        resp_data: Dict = resp.json()
        return try_get(resp_data, "state") == "PAID"

    async def expire_invoice(self, invoice_id):
        resp: Response = await self._client.patch(f"/invoices/{invoice_id}/cancel")
        resp_data: Dict = resp.json()
        return try_get(resp_data, "state") == "CANCELLED"

    async def get_bitcoin_price(self):
        # TODO: implement
        raise NotImplementedError("")
        # response: Response = await self._client.get("/prices/BTC-USD/spot")
        # if not successful_response(response):
        #     return error("Failed to get bitcoin price", data=response)
        # json = response.json()
        # if not json:
        #     return error("Failed to parse json resposne", data=response)
        # resp_data = try_get(json, "data")
        # if not resp_data:
        #     return error("No response data", data=json)
        # doc_data = {**resp_data, "_id": int(time.time())}
        # doc = CoinbasePrice(**doc_data).to_dict()
        # return success(data=doc)


class LNbits(PaymentProcessor):
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


class OpenNode(PaymentProcessor):
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


def init_price_provider():
    from lib.abbot.env import PAYMENT_PROCESSOR_TOKEN

    available_providers = ["coinbase", "strike"]
    if PRICE_PROVIDER_KIND is None or PRICE_PROVIDER_KIND not in available_providers:
        raise Exception(f"PRICE_PROVIDER_KIND must be one of {', '.join(available_providers)}")
    if PRICE_PROVIDER_KIND == "strike":
        return Strike(PAYMENT_PROCESSOR_TOKEN)
    elif PRICE_PROVIDER_KIND == "coinbase":
        return Coinbase()


class CoinbasePrice:
    def __init__(self, _id, amount, base, currency):
        self._id: int = _id
        self.amount: float = float(amount)
        self.base: str = base
        self.currency: str = currency

    def to_dict(self):
        return vars(self)


class Provider(ABC):
    @abstractmethod
    def get_bitcoin_price(self):
        pass


class Coinbase(Provider):
    def __init__(self, api_key=None):
        super().__init__()
        self._client = httpx.AsyncClient(
            base_url="https://api.coinbase.com/v2",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    async def get_bitcoin_price(self):
        log_name: str = f"{FILE_NAME}: get_bitcoin_price"
        response: Response = await self._client.get("/prices/BTC-USD/spot")
        if not successful_response(response):
            return error("Failed to get bitcoin price", data=response)
        json = response.json()
        if not json:
            return error("Failed to parse json resposne", data=response)
        resp_data = try_get(json, "data")
        if not resp_data:
            return error("No response data", data=json)
        price_data = {**resp_data, "_id": int(time.time())}
        price_doc: CoinbasePrice = CoinbasePrice(**price_data).to_dict()
        insert_result: InsertOneResult = mongo_abbot.insert_one_price(price_doc)
        if not successful_insert_one(insert_result):
            error_message = f"response={response} \n json={json} \n resp_data={resp_data}"
            error_message = f"{error_message} \n price_data={price_data} \n price_doc={price_doc}"
            error_message = f"{error_message} \n insert_result={insert_result}"
            error_bot.log(log_name, error_message)
        return success(data=price_doc, amount=try_get(price_doc, "amount"))


def init_payment_processor() -> Strike | LNbits | OpenNode:
    from lib.abbot.env import PAYMENT_PROCESSOR_TOKEN

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
