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
            '--silent',
            type=int,
            default=0,
            choices=[0, 1],
            help='Silently fall if such snapshot exist',
        )

    def _handle(self, *args, **options):
        commit_name = options['name']
        silent = bool(options['silent'])
        exists = Snapshot.objects.filter(name=commit_name).exists()

        if exists and not silent:
            raise CommandError(
                'Snapshot with given name already exists',
            )
        elif exists:
            self.stdout.write('Snapshot with given name already exists')
            sys.exit(0)

        latest = Snapshot.objects.filter(applied=True).last()
        if latest is not None and latest.consistent_state:
            self.stdout.write('All migrations saved in currently applied snapshot. Nothing to create')
            sys.exit(0)
        with transaction.atomic():
            if latest is not None:
                latest.applied = False
                latest.save(update_fields=['applied'])
            migrations = self._latest_migrations().only('id', 'app', 'name')
            snapshot = Snapshot(name=commit_name, applied=True)
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
