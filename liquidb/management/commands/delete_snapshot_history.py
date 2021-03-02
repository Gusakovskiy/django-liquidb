from django.db import transaction

from ._private import BaseLiquidbRevertCommand
from ...models import Snapshot


class Command(BaseLiquidbRevertCommand):
    help = 'Delete all history of snapshots'

    def _handle(self, *args, **options):
        # TODO add --force argument and ask before delete
        with transaction.atomic():
            _total, models = Snapshot.objects.all().delete()
            snapshots = models['liquidb.Snapshot']
            migrations_states = models['liquidb.MigrationState']
        self.stdout.write(f'Successfully deleted history of {snapshots} snaphots and {migrations_states} migrations')
