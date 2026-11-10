from decimal import Decimal

from django.test import SimpleTestCase

from flights.rules import evaluate_alert


def decide(**overrides):
    params = dict(
        price=Decimal("100"),
        below_price=None,
        drop_percent=None,
        history=[],
        last_alerted_price=None,
        min_samples=3,
    )
    params.update(overrides)
    return evaluate_alert(**params)


class EvaluateAlertTests(SimpleTestCase):
    def test_no_rules_no_alert(self):
        self.assertFalse(decide().should_alert)

    def test_below_price_triggers(self):
        decision = decide(price=Decimal("150"), below_price=Decimal("200"))
        self.assertTrue(decision.should_alert)
        self.assertIn("por debajo de 200", decision.reason)

    def test_above_price_threshold_does_not_trigger(self):
        self.assertFalse(decide(price=Decimal("250"), below_price=Decimal("200")).should_alert)

    def test_drop_vs_average_triggers_with_enough_history(self):
        history = [Decimal("200")] * 5
        decision = decide(price=Decimal("150"), drop_percent=20, history=history)
        self.assertTrue(decision.should_alert)  # 150 <= 200 * 0.8

    def test_drop_vs_average_needs_min_samples(self):
        decision = decide(price=Decimal("150"), drop_percent=20, history=[Decimal("200")] * 2)
        self.assertFalse(decision.should_alert)

    def test_drop_vs_average_not_enough_drop(self):
        history = [Decimal("200")] * 5
        self.assertFalse(decide(price=Decimal("170"), drop_percent=20, history=history).should_alert)

    def test_no_repeat_alert_at_same_or_higher_price(self):
        decision = decide(
            price=Decimal("150"), below_price=Decimal("200"), last_alerted_price=Decimal("150")
        )
        self.assertFalse(decision.should_alert)

    def test_alert_again_on_new_lower_minimum(self):
        decision = decide(
            price=Decimal("140"), below_price=Decimal("200"), last_alerted_price=Decimal("150")
        )
        self.assertTrue(decision.should_alert)
