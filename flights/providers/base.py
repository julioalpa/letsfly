"""Contrato común para cualquier proveedor de tarifas.

Si mañana cambiás de API (Duffel, Kiwi, otra), sólo hay que escribir otro cliente
que devuelva listas de Offer. El resto del proyecto no se entera.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Offer:
    price: Decimal
    currency: str
    carrier: str
    departure_date: date
    stops: int
    ignav_id: str = ""


class ProviderError(Exception):
    """Error al consultar un proveedor (red, auth, respuesta inesperada)."""
