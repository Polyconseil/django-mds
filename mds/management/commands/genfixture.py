from django.core.management.base import BaseCommand
from mds import factories


class Command(BaseCommand):
    help = "Create a service area and 100 devices"

    def add_arguments(self, parser):
        parser.add_argument(
            "--records_count", nargs="?", default=1000, dest="records_count", type=int
        )

    def handle(self, *args, **options):
        factories.Area(
            label="District 10", polygons=[factories.Polygon(), factories.Polygon()]
        )
        factories.EventRecord.create_batch(options["records_count"])
