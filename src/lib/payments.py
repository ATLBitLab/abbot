from abc import ABC, abstractmethod
from .utils import http_request, try_get


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

    _base_url = "https://api.strike.me/v1"

    def __init__(self, api_key):
        super().__init__()
        assert (api_key is not None, "a Strike API key must be supplied")
        self.api_key = api_key

    def get_invoice(self, correlation_id, description):
        invoice_resp = self.__make_request(
            "POST",
            f"{self._base_url}/invoices",
            {
                "correlationId": correlation_id,
                "description": description,
                "amount": {"amount": "1.00", "currency": "USD"},
            },
        )
        invoice_id = try_get(invoice_resp, "invoiceId")
        quote_resp = self.__make_request(
            "POST", f"{self._base_url}/invoices/{invoice_id}/quote"
        )

        return (
            invoice_id,
            try_get(quote_resp, "lnInvoice"),
            try_get(quote_resp, "expirationInSec"),
        )

    def invoice_is_paid(self, invoice_id):
        resp = self.__make_request("GET", f"{self._base_url}/invoices/{invoice_id}")
        return try_get(resp, "state") == "PAID"

    def expire_invoice(self, invoice_id):
        resp = self.__make_request(
            "PATCH", f"{self._base_url}/invoices/{invoice_id}/cancel"
        )
        return try_get(resp, "state") == "CANCELLED"

    def __make_request(self, method, path, body):
        return http_request(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method,
            path,
            body,
        )
