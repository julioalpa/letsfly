from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Route(models.Model):
    """Una búsqueda que querés vigilar: ruta, ventana de fechas, filtros y reglas de alerta."""

    name = models.CharField("nombre", max_length=120)
    origin = models.CharField("origen (IATA)", max_length=3)
    destination = models.CharField("destino (IATA)", max_length=3)
    date_from = models.DateField("salida desde")
    date_to = models.DateField("salida hasta")

    # Filtros: se mandan a la API sólo si están completos.
    max_stops = models.PositiveSmallIntegerField("máx. escalas", null=True, blank=True)
    cabin_class = models.CharField(
        "cabina",
        max_length=20,
        default="economy",
        choices=[
            ("economy", "Económica"),
            ("premium_economy", "Premium economy"),
            ("business", "Business"),
            ("first", "Primera"),
        ],
    )
    airlines_include = models.CharField(
        "aerolíneas (códigos separados por coma)",
        max_length=120,
        blank=True,
        help_text="Ej: AR,JA,4M. Vacío = todas.",
    )

    # Reglas de alerta. Pueden combinarse; cualquiera que se cumpla dispara el aviso.
    alert_below_price = models.DecimalField(
        "avisar si baja de", max_digits=12, decimal_places=2, null=True, blank=True
    )
    alert_drop_percent = models.PositiveSmallIntegerField(
        "avisar si baja % vs. promedio",
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(99)],
        help_text="Compara contra el promedio histórico de esa fecha.",
    )

    is_active = models.BooleanField("activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "ruta"
        verbose_name_plural = "rutas"

    def __str__(self):
        return f"{self.name} ({self.origin}→{self.destination})"

    def clean(self):
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValidationError({"date_to": "La fecha final no puede ser anterior a la inicial."})

    def departure_dates(self):
        """Todas las fechas de salida de la ventana, una request por fecha."""
        day = self.date_from
        while day <= self.date_to:
            yield day
            day += timedelta(days=1)


class PriceObservation(models.Model):
    """Precio más bajo que devolvió la API para una ruta y fecha, en un momento dado."""

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="observations")
    departure_date = models.DateField("fecha de salida")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    carrier = models.CharField(max_length=80, blank=True)
    stops = models.PositiveSmallIntegerField(null=True, blank=True)
    ignav_id = models.CharField(max_length=64, blank=True)
    observed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at"]
        indexes = [models.Index(fields=["route", "departure_date", "observed_at"])]
        verbose_name = "observación de precio"
        verbose_name_plural = "historial de precios"

    def __str__(self):
        return f"{self.route_id} {self.departure_date} {self.price} {self.currency}"


class Notification(models.Model):
    """Aviso ya enviado. Sirve para no repetir alertas por el mismo precio."""

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="notifications")
    departure_date = models.DateField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    reason = models.CharField(max_length=200)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = "aviso enviado"
        verbose_name_plural = "avisos enviados"

    def __str__(self):
        return f"aviso {self.route_id} {self.departure_date} {self.price}"
