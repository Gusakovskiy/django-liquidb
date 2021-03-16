from django.core.exceptions import ObjectDoesNotExist
from django.core.management import CommandError

from ._private import BaseLiquidbRevertCommand
from ...models import Snapshot


class Command(BaseLiquidbRevertCommand):
    help = 'Revert migration to latest commit (snapshot)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            type=int,
            default=0,
            choices=[0, 1],
            help='Drop unsaved changes',
        )

    def _handle(self, *args, **options):
        try:
            snapshot = Snapshot.objects.latest('id')
        except ObjectDoesNotExist as error:
            raise CommandError('No latest snapshot present') from error
        self._checkout_snapshot(snapshot, force=bool(options['force']))
