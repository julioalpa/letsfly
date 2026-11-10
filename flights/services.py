"""Orquesta una consulta: pide precios, guarda historial, evalúa reglas y avisa."""
from dataclasses import dataclass, field

from django.conf import settings
from django.db.models import Min

from .models import Notification, PriceObservation, Route
from .notifiers import NotificationError, get_notifier
from .providers.base import ProviderError
from .providers.ignav import IgnavClient
from .rules import evaluate_alert


@dataclass
class PollResult:
    route: Route
    dates_checked: int = 0
    observations: int = 0
    alerts: int = 0
    errors: list = field(default_factory=list)


def parse_airlines(raw):
    return [code.strip().upper() for code in raw.split(",") if code.strip()]


def offers_for_route(route, provider, day):
    """Ofertas de una fecha, ya filtradas por los requisitos de la ruta."""
    offers = provider.search_one_way(
        origin=route.origin,
        destination=route.destination,
        departure_date=day,
        max_stops=route.max_stops,
        cabin_class=route.cabin_class,
        airlines_include=parse_airlines(route.airlines_include) or None,
    )
    # Doble chequeo local: no confiamos ciegamente en que la API respete todos los filtros.
    if route.max_stops is not None:
        offers = [o for o in offers if o.stops <= route.max_stops]
    if route.airlines_include:
        allowed = set(parse_airlines(route.airlines_include))
        offers = [o for o in offers if o.carrier.upper() in allowed]
    return offers


def poll_route(route, *, provider=None, notifier=None):
    provider = provider or IgnavClient()
    notifier = notifier or get_notifier()
    result = PollResult(route=route)

    for day in route.departure_dates():
        result.dates_checked += 1
        try:
            offers = offers_for_route(route, provider, day)
        except ProviderError as exc:
            result.errors.append(f"{day}: {exc}")
            continue
        if not offers:
            continue

        best = min(offers, key=lambda o: o.price)

        # Historial previo de esa fecha, antes de guardar el precio nuevo.
        history = list(
            PriceObservation.objects.filter(
                route=route, departure_date=day, currency=best.currency
            ).values_list("price", flat=True)
        )
        last_alerted = Notification.objects.filter(
            route=route, departure_date=day, currency=best.currency
        ).aggregate(low=Min("price"))["low"]

        PriceObservation.objects.create(
            route=route,
            departure_date=day,
            price=best.price,
            currency=best.currency,
            carrier=best.carrier,
            stops=best.stops,
            ignav_id=best.ignav_id,
        )
        result.observations += 1

        decision = evaluate_alert(
            price=best.price,
            below_price=route.alert_below_price,
            drop_percent=route.alert_drop_percent,
            history=history,
            last_alerted_price=last_alerted,
            min_samples=settings.PRICE_HISTORY_MIN_SAMPLES,
        )
        if not decision.should_alert:
            continue

        text = (
            f"✈️ {route.name}\n"
            f"{day:%d/%m/%Y}: {best.price} {best.currency} · {best.carrier or 'sin dato de aerolínea'} · "
            f"{best.stops} escala(s)\n"
            f"Motivo: {decision.reason}"
        )
        try:
            notifier.send(text)
        except NotificationError as exc:
            result.errors.append(f"{day}: aviso no enviado: {exc}")
            continue

        Notification.objects.create(
            route=route,
            departure_date=day,
            price=best.price,
            currency=best.currency,
            reason=decision.reason[:200],
        )
        result.alerts += 1

    return result
