import sys

from django.core.exceptions import ObjectDoesNotExist

from ._private import BaseLiquidbRevertCommand
from ...models import Snapshot


class Command(BaseLiquidbRevertCommand):
    help = 'Revert migration state to given commit (snapshot)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            help='More verbose name of commit (snapshot)',
        )
        parser.add_argument(
            '--force',
            type=bool,
            default=False,
            help='Drop unsaved changes',
        )

    def get_snapshots(self, name: str):
        try:
            snapshots = Snapshot.objects.get(name=name)
        except ObjectDoesNotExist as e:
            self.stderr.write('{!r}'.format(e))
            sys.exit(2)
        return snapshots

    def _handle(self, *args, **options):
        snapshots = self.get_snapshots(options['name'])
        self._checkout_snapshot(snapshots, force=options['force'])
