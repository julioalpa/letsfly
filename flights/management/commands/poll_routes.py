from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from flights.models import Route
from flights.services import poll_route


class Command(BaseCommand):
    help = "Consulta precios de las rutas activas, guarda historial y envía avisos."

    def add_arguments(self, parser):
        parser.add_argument("--route", type=int, help="ID de una sola ruta")

    def handle(self, *args, **options):
        if not settings.IGNAV_API_KEY:
            raise CommandError("Falta IGNAV_API_KEY en el entorno.")

        routes = Route.objects.filter(is_active=True)
        if options["route"]:
            routes = routes.filter(pk=options["route"])

        for route in routes:
            result = poll_route(route)
            self.stdout.write(
                f"{route}: {result.dates_checked} fechas, "
                f"{result.observations} precios guardados, {result.alerts} avisos, "
                f"{len(result.errors)} errores"
            )
            for error in result.errors[:5]:
                self.stderr.write(f"  ! {error}")
