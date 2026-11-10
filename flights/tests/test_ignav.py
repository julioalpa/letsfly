from datetime import date
from decimal import Decimal
from unittest import mock

import requests
from django.test import SimpleTestCase

from flights.providers.base import ProviderError
from flights.providers.ignav import IgnavClient, parse_itineraries


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


SAMPLE_PAYLOAD = {
    "origin": "EZE",
    "destination": "MAD",
    "departure_date": "2027-03-10",
    "itineraries": [
        {
            "ignav_id": "abc123",
            "price": {"amount": 799, "currency": "USD", "status": "verified"},
            "outbound": {
                "carrier": "AR",
                "duration_minutes": 840,
                "segments": [{"flight_number": "1"}, {"flight_number": "2"}],
            },
        },
        {
            "ignav_id": "def456",
            "price": {"amount": 950, "currency": "USD"},
            "outbound": {"carrier": "IB", "segments": [{"flight_number": "3"}]},
        },
        {"ignav_id": "roto"},  # sin precio: se ignora
    ],
}


class ParseItinerariesTests(SimpleTestCase):
    def test_parses_price_carrier_stops_and_id(self):
        offers = parse_itineraries(SAMPLE_PAYLOAD, date(2027, 3, 10))
        self.assertEqual(len(offers), 2)
        first = offers[0]
        self.assertEqual(first.price, Decimal("799"))
        self.assertEqual(first.currency, "USD")
        self.assertEqual(first.carrier, "AR")
        self.assertEqual(first.stops, 1)  # 2 segmentos = 1 escala
        self.assertEqual(first.ignav_id, "abc123")
        self.assertEqual(offers[1].stops, 0)

    def test_empty_payload(self):
        self.assertEqual(parse_itineraries({}, date(2027, 3, 10)), [])


class IgnavClientTests(SimpleTestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.client = IgnavClient(api_key="test-key", base_url="https://example.test/api", session=self.session)

    def test_sends_only_defined_filters(self):
        self.session.post.return_value = FakeResponse(200, SAMPLE_PAYLOAD)
        self.client.search_one_way(
            origin="EZE", destination="MAD", departure_date=date(2027, 3, 10), max_stops=1
        )
        args, kwargs = self.session.post.call_args
        self.assertEqual(args[0], "https://example.test/api/fares/one-way")
        self.assertEqual(kwargs["json"], {"origin": "EZE", "destination": "MAD", "departure_date": "2027-03-10", "max_stops": 1})
        self.assertEqual(kwargs["headers"]["X-Api-Key"], "test-key")

    def test_non_200_raises_provider_error(self):
        self.session.post.return_value = FakeResponse(401, text="unauthorized")
        with self.assertRaises(ProviderError):
            self.client.search_one_way(origin="EZE", destination="MAD", departure_date=date(2027, 3, 10))

    def test_network_error_raises_provider_error(self):
        self.session.post.side_effect = requests.ConnectionError("boom")
        with self.assertRaises(ProviderError):
            self.client.search_one_way(origin="EZE", destination="MAD", departure_date=date(2027, 3, 10))

    def test_missing_key_raises_before_calling(self):
        client = IgnavClient(api_key="", session=self.session)
        with self.assertRaises(ProviderError):
            client.search_one_way(origin="EZE", destination="MAD", departure_date=date(2027, 3, 10))
        self.session.post.assert_not_called()
