import sys

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from django.db import connection
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

    def _snapshot_exists(self, from_id, to_id, state):
        return Snapshot.objects.filter(id__gt=from_id, id__lt=to_id, applied=state).exists()

    def get_latest_applied(self):
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
            self.stderr.write(f'Empty target version for snapshot {snapshot.name}')
            sys.exit(2)
        executor = MigrationExecutor(self.connection)
        _: ProjectState = executor.migrate(targets)

    def _checkout_snapshot(self, snapshot: Snapshot, force=False):
        latest = self.get_latest_applied()
        consistent_with_migration_table = latest.consistent_state
        if not consistent_with_migration_table and not force:
            self.stderr.write(
                f'Migration state is inconsistent latest applied snapshot do not has all currently applied migrations. '
                f'Please use --force flag to checkout anyway.'
            )
            sys.exit(2)
        if not consistent_with_migration_table:
            self.stdout.write('Force to apply migration. Unsaved changes will be dropped')

        if snapshot.id > latest.id:
            from_id = latest.id
            to_id = snapshot.id
            if self._snapshot_exists(from_id, to_id, True):
                self.stderr.write(f'Inconsistent history; Applied snapshots exists between {from_id} and {to_id}')
                sys.exit(2)
            # to the future
            self._revert_to_snapshot(snapshot)
            # update state that all previous transactions applied
            Snapshot.objects.filter(id__lte=snapshot.id).update(applied=True)
        elif snapshot.id < latest.id:
            from_id = snapshot.id
            to_id = latest.id
            if self._snapshot_exists(from_id, to_id, False):
                self.stderr.write(f'Inconsistent history; Applied snapshots exists between {from_id} and {to_id}')
                sys.exit(2)
            # back to the future
            self._revert_to_snapshot(snapshot)
            # update state that all previous transactions unaplied
            Snapshot.objects.filter(id__gt=snapshot.id).update(applied=False)
        else:
            # eq is not same as equal snapshot.id == latest.id
            if snapshot == latest:
                # migration hashes are the same
                # nothing to do
                self.stdout(f'Snapshot already applied {latest.name}')
                sys.exit(0)
            else:
                # should happen ?
                self._revert_to_snapshot(snapshot)
        self.stdout(f'Checkout from snapshot {latest.name} to {snapshot.name}')
