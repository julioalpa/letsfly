from django.contrib import admin

from .models import Notification, PriceObservation, Route


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "origin",
        "destination",
        "date_from",
        "date_to",
        "max_stops",
        "cabin_class",
        "alert_below_price",
        "alert_drop_percent",
        "is_active",
    )
    list_editable = ("is_active",)
    list_filter = ("is_active", "cabin_class", "max_stops")
    search_fields = ("name", "origin", "destination")


@admin.register(PriceObservation)
class PriceObservationAdmin(admin.ModelAdmin):
    list_display = ("route", "departure_date", "price", "currency", "carrier", "stops", "observed_at")
    list_filter = ("route", "currency")
    date_hierarchy = "observed_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("route", "departure_date", "price", "currency", "reason", "sent_at")
    list_filter = ("route",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
