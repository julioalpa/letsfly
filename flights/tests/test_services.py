from datetime import date
from decimal import Decimal

from django.test import TestCase, override_settings

from flights.models import Notification, PriceObservation, Route
from flights.notifiers import NotificationError
from flights.providers.base import Offer, ProviderError
from flights.services import parse_airlines, poll_route


class FakeProvider:
    """Devuelve precios fijos por fecha, o levanta error si se lo pedís."""

    def __init__(self, prices_by_day=None, fail_on=None):
        self.prices_by_day = prices_by_day or {}
        self.fail_on = fail_on or set()
        self.calls = []

    def search_one_way(self, *, origin, destination, departure_date, max_stops=None, cabin_class=None, airlines_include=None):
        self.calls.append((departure_date, max_stops, cabin_class, airlines_include))
        if departure_date in self.fail_on:
            raise ProviderError("caída simulada")
        price = self.prices_by_day.get(departure_date)
        if price is None:
            return []
        return [
            Offer(
                price=Decimal(price),
                currency="USD",
                carrier="AR",
                departure_date=departure_date,
                stops=0,
                ignav_id=f"id-{departure_date}",
            )
        ]


class FakeNotifier:
    def __init__(self, fail=False):
        self.messages = []
        self.fail = fail

    def send(self, text):
        if self.fail:
            raise NotificationError("sin red")
        self.messages.append(text)


@override_settings(PRICE_HISTORY_MIN_SAMPLES=2)
class PollRouteTests(TestCase):
    def setUp(self):
        self.route = Route.objects.create(
            name="EZE-MAD",
            origin="EZE",
            destination="MAD",
            date_from=date(2027, 3, 10),
            date_to=date(2027, 3, 12),
            alert_below_price=Decimal("800"),
        )
        self.d1, self.d2, self.d3 = date(2027, 3, 10), date(2027, 3, 11), date(2027, 3, 12)

    def test_stores_one_observation_per_date_with_offers(self):
        provider = FakeProvider({self.d1: "900", self.d2: "850"})
        result = poll_route(self.route, provider=provider, notifier=FakeNotifier())
        self.assertEqual(result.dates_checked, 3)
        self.assertEqual(result.observations, 2)
        self.assertEqual(PriceObservation.objects.filter(route=self.route).count(), 2)

    def test_alerts_when_below_threshold_and_records_notification(self):
        provider = FakeProvider({self.d1: "750"})
        notifier = FakeNotifier()
        result = poll_route(self.route, provider=provider, notifier=notifier)
        self.assertEqual(result.alerts, 1)
        self.assertEqual(len(notifier.messages), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_does_not_repeat_same_price(self):
        provider = FakeProvider({self.d1: "750"})
        notifier = FakeNotifier()
        poll_route(self.route, provider=provider, notifier=notifier)
        result = poll_route(self.route, provider=provider, notifier=notifier)
        self.assertEqual(result.alerts, 0)
        self.assertEqual(len(notifier.messages), 1)

    def test_provider_error_is_collected_not_raised(self):
        provider = FakeProvider({self.d2: "900"}, fail_on={self.d1})
        result = poll_route(self.route, provider=provider, notifier=FakeNotifier())
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.observations, 1)

    def test_failed_notification_does_not_record_alert(self):
        provider = FakeProvider({self.d1: "750"})
        result = poll_route(self.route, provider=provider, notifier=FakeNotifier(fail=True))
        self.assertEqual(result.alerts, 0)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(len(result.errors), 1)

    def test_passes_filters_to_provider(self):
        self.route.max_stops = 1
        self.route.airlines_include = "ar, ib"
        self.route.save()
        provider = FakeProvider()
        poll_route(self.route, provider=provider, notifier=FakeNotifier())
        self.assertEqual(provider.calls[0], (self.d1, 1, "economy", ["AR", "IB"]))

    def test_local_filter_drops_offers_over_max_stops(self):
        self.route.max_stops = 0
        self.route.save()

        class StopsProvider(FakeProvider):
            def search_one_way(self, **kwargs):
                return [
                    Offer(Decimal("500"), "USD", "AR", kwargs["departure_date"], stops=2, ignav_id="x")
                ]

        result = poll_route(self.route, provider=StopsProvider(), notifier=FakeNotifier())
        self.assertEqual(result.observations, 0)


class HelperTests(TestCase):
    def test_parse_airlines(self):
        self.assertEqual(parse_airlines(" ar, ,ib ,4m"), ["AR", "IB", "4M"])
        self.assertEqual(parse_airlines(""), [])
