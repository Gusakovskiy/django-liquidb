from ._private import BaseLiquidbRevertCommand
from ...models import Snapshot


class Command(BaseLiquidbRevertCommand):
    help = 'Revert migration to latest commit (snapshot)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            type=bool,
            default=False,
            help='Drop unsaved changes',
        )

    def _handle(self, *args, **options):
        snapshot = Snapshot.objects.latest('id')
        self._checkout_snapshot(snapshot, force=options['force'])
