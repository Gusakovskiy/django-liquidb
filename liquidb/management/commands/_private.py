import sys

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.state import ProjectState

from ...models import Snapshot, MigrationState, get_latest_applied_migrations_qs


class BaseLiquidbCommand(BaseCommand):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = connection

    def _check_migration_db_exists(self):
        recorder = MigrationRecorder(self.connection)
        if not recorder.has_table():
            self.stderr.write('No migration table present')
            sys.exit(2)

    def _check_liquidb_tables_exists(self):
        with self.connection.cursor() as cursor:
            tables = self.connection.introspection.table_names(cursor)
        tables_to_check = [Snapshot._meta.db_table, MigrationState._meta.db_table]  # NOQA
        if tables and tables_to_check:
            return all(map(lambda x: x in tables, tables_to_check))
        return False

    def _init(self):
        self._check_migration_db_exists()
        self._check_liquidb_tables_exists()

    def _handle(self, *args, **options):
        raise NotImplemented('Override this method')

    def handle(self, *args, **options):
        self._init()
        self._handle(*args, **options)

    def _latest_migrations(self):
        return get_latest_applied_migrations_qs(self.connection)


class BaseLiquidbRevertCommand(BaseLiquidbCommand):

    def get_applied_snapshot(self):
        try:
            latest = Snapshot.objects.filter(applied=True).latest('id')
        except ObjectDoesNotExist as e:
            self.stderr.write('No latest snapshot present; {!r}'.format(e))
            sys.exit(2)
        return latest

    def _revert_to_snapshot(self, snapshot: Snapshot):
        targets = snapshot.migrations.values_list('app', 'name')
        if not targets:
            # snapshot that do not have any migrations
            # TODO get all apps from django apps and migrate everything to zero ?
            self.stderr.write(f'No connected migrations found for snapshot {snapshot.name}')
            sys.exit(2)
        executor = MigrationExecutor(self.connection)
        _: ProjectState = executor.migrate(targets)

    def _checkout_snapshot(self, snapshot: Snapshot, force=False):
        latest = self.get_applied_snapshot()
        consistent_with_migration_table = latest.consistent_state
        if not consistent_with_migration_table and not force:
            self.stderr.write(
                f'Migration state is inconsistent latest applied snapshot do not has all currently applied migrations. '
                f'Please use --force flag to checkout anyway.'
            )
            sys.exit(2)
        if not consistent_with_migration_table:
            self.stdout.write('Force to apply migration. Unsaved changes will be dropped')

        # eq is not same as equal snapshot.id == latest.id
        # see liquidb.models.Snapshot.__eq__
        if snapshot == latest:
            # migration hashes are the same
            # nothing to do
            self.stdout.write(f'Snapshot already applied {latest.name}')
            sys.exit(0)
        self._revert_to_snapshot(snapshot)
        with transaction.atomic():
            latest.applied = False
            latest.save(update_fields=['applied'])

            snapshot.applied = True
            snapshot.save(update_fields=['applied'])

        self.stdout.write(f'Checkout from snapshot {latest.name} to {snapshot.name}')
