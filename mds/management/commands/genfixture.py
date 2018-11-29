from django.core.management.base import BaseCommand
from mds import factories


class Command(BaseCommand):
    help = "Create a service area and 100 devices"

    def handle(self, *args, **options):
        factories.Area.create()
        for _i in range(100):
            factories.Device.create()
