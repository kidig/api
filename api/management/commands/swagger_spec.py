import yaml
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string

from ...swagger import validate


class Command(BaseCommand):
    def handle(self, *args, **options):
        router = import_string(settings.API_DEFAULT_ROUTER)
        spec = router.swagger()
        validate(spec)
        self.stdout.write(yaml.dump(spec))
