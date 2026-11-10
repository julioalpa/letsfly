"""Cliente mínimo para la API de Ignav (tarifas de ida).

Docs: https://ignav.com/docs/quickstart
Auth: header X-Api-Key. Endpoint: POST {base}/fares/one-way
"""
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings

from .base import Offer, ProviderError


class IgnavClient:
    def __init__(self, api_key=None, base_url=None, timeout=None, session=None):
        self.api_key = settings.IGNAV_API_KEY if api_key is None else api_key
        self.base_url = (base_url or settings.IGNAV_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.IGNAV_TIMEOUT_SECONDS
        self.session = session or requests.Session()

    def search_one_way(
        self,
        *,
        origin,
        destination,
        departure_date,
        max_stops=None,
        cabin_class=None,
        airlines_include=None,
    ):
        if not self.api_key:
            raise ProviderError("Falta IGNAV_API_KEY en el entorno")

        body = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date.isoformat(),
        }
        # Sólo mandamos los filtros que el usuario definió.
        if max_stops is not None:
            body["max_stops"] = max_stops
        if cabin_class:
            body["cabin_class"] = cabin_class
        if airlines_include:
            # TODO: confirmar en la doc si Ignav espera lista o string.
            body["airlines_include"] = airlines_include

        try:
            resp = self.session.post(
                f"{self.base_url}/fares/one-way",
                json=body,
                headers={"X-Api-Key": self.api_key, "Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"Error de red con Ignav: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"Ignav respondió {resp.status_code}: {resp.text[:200]}")

        try:
            payload = resp.json()
        except ValueError as exc:
            raise ProviderError("Ignav devolvió una respuesta que no es JSON") from exc

        return parse_itineraries(payload, departure_date)


def parse_itineraries(payload, departure_date):
    """Convierte la respuesta de Ignav en una lista de Offer. Ignora ítems incompletos."""
    offers = []
    for item in payload.get("itineraries") or []:
        price = item.get("price") or {}
        try:
            amount = Decimal(str(price["amount"]))
        except (KeyError, TypeError, InvalidOperation):
            continue

        outbound = item.get("outbound") or {}
        segments = outbound.get("segments") or []
        offers.append(
            Offer(
                price=amount,
                currency=price.get("currency") or "USD",
                carrier=outbound.get("carrier") or "",
                departure_date=departure_date if isinstance(departure_date, date) else date.fromisoformat(departure_date),
                stops=max(len(segments) - 1, 0),
                ignav_id=item.get("ignav_id") or "",
            )
        )
    return offers
