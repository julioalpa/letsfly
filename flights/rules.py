"""Reglas de alerta. Funciones puras: sin base de datos ni red, fáciles de testear."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Sequence


@dataclass(frozen=True)
class AlertDecision:
    should_alert: bool
    reason: str = ""


def average(prices: Sequence[Decimal]) -> Decimal:
    return sum(prices, Decimal("0")) / len(prices)


def evaluate_alert(
    *,
    price: Decimal,
    below_price: Optional[Decimal],
    drop_percent: Optional[int],
    history: Sequence[Decimal],
    last_alerted_price: Optional[Decimal],
    min_samples: int,
) -> AlertDecision:
    """Decide si conviene avisar por este precio.

    - history: precios previos de la misma fecha de salida (sin contar el actual).
    - last_alerted_price: el precio más bajo que ya se avisó para esa fecha.
      Sólo se vuelve a avisar si el precio es nuevo mínimo, así no hay spam.
    """
    if last_alerted_price is not None and price >= last_alerted_price:
        return AlertDecision(False, "sin cambio desde el último aviso")

    reasons = []

    if below_price is not None and price <= below_price:
        reasons.append(f"por debajo de {below_price}")

    if drop_percent and len(history) >= min_samples:
        avg = average(history)
        threshold = avg * (Decimal(100 - drop_percent) / Decimal(100))
        if price <= threshold:
            reasons.append(f"{drop_percent}% debajo del promedio ({avg:.2f})")

    if reasons:
        return AlertDecision(True, "; ".join(reasons))
    return AlertDecision(False, "ninguna regla cumplida")
