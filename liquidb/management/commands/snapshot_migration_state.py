import sys

from ._private import BaseLiquidbCommand
from ...models import Snapshot, MigrationState


class Command(BaseLiquidbCommand):
    help = 'Create snapshot of migration state.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            help='Verbose name of snapshot',
        )

    def _handle(self, *args, **options):
        commit_name = options['name']
        exists = Snapshot.objects.filter(name=commit_name).exists()
        if exists:
            self.stderr.write('Snapshot with given name already exists')
            sys.exit(2)
        latest = Snapshot.objects.filter(applied=True).first()
        if latest is not None and latest.consistent_state:
            self.stderr.write('All migrations saved in previous applied snapshot. Nothing to create')
            sys.exit(1)
        snapshot = Snapshot(name=commit_name)
        snapshot.save()
        migrations = self._latest_migrations().only('id', 'app', 'name')
        to_create = [
            MigrationState(
                snapshot=snapshot,
                migration_id=migration.id,
                app=migration.app,
                name=migration.name,
            )
            for migration in migrations
        ]
        MigrationState.objects.bulk_create(to_create, batch_size=1000, ignore_conflicts=True)
