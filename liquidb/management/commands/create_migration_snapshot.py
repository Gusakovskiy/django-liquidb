import sys

from django.core.management import CommandError
from django.db import transaction

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
        parser.add_argument(
            '--overwrite',
            type=int,
            default=0,
            choices=[0, 1],
            help='If snapshot with given name exist it will overwrite it',
        )

    def _handle(self, *args, **options):
        snapshot_name = options['name']
        overwrite = bool(options['overwrite'])
        exists = Snapshot.objects.filter(name=snapshot_name).exists()
        if exists and not overwrite:
            raise CommandError(
                'Snapshot with given name already exists.\n'
                'Please use overwrite to execute it anyway',
            )

        if exists:
            snapshot = Snapshot.objects.get(name=snapshot_name)
        else:
            snapshot = Snapshot(name=snapshot_name)
        latest = Snapshot.objects.filter(applied=True).last()
        if latest is not None and latest.consistent_state:
            self.stdout.write('All migrations saved in currently applied snapshot. Nothing to create')
            sys.exit(0)
        with transaction.atomic():
            if latest is not None:
                latest.applied = False
                latest.save(update_fields=['applied'])
            migrations = self._latest_migrations().only('id', 'app', 'name')
            snapshot.applied = True

            if snapshot.id is not None:
                # in overwrite mode
                # so we need to delete all previous migrations
                # from this snapshot
                snapshot.migrations.all().delete()
            snapshot.save()
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
            self.stdout.write(f'Snapshot "{snapshot_name}" successfully save')
