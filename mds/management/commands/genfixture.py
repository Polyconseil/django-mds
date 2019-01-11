from django.core.management.base import BaseCommand
from mds import factories


class Command(BaseCommand):
    help = "Create a service area and 100 devices"

    def handle(self, *args, **options):
        factories.Area(
            label="District 10", polygons=[factories.Polygon(), factories.Polygon()]
        )
        factories.Telemetry.create_batch(1000)
