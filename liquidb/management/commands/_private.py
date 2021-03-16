import sys
from abc import ABCMeta, abstractmethod

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.state import ProjectState

from ...models import Snapshot, MigrationState, get_latest_applied_migrations_qs


class BaseLiquidbCommand(BaseCommand, metaclass=ABCMeta):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = connection

    def _check_migration_db_exists(self):
        recorder = MigrationRecorder(self.connection)
        if not recorder.has_table():
            raise CommandError('No migration table present')

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

    def handle(self, *args, **options):
        self._init()
        self._handle(*args, **options)

    def _latest_migrations(self):
        return get_latest_applied_migrations_qs(self.connection)

    @staticmethod
    def get_snapshot(name: str) -> Snapshot:
        """Retrun snapshot by name"""
        try:
            snapshot = Snapshot.objects.get(name=name)
        except ObjectDoesNotExist as error:
            raise CommandError(f'Snapshot with name: "{name}" doesn\'t exists') from error
        return snapshot

    @abstractmethod
    def _handle(self, *args, **options):
        raise NotImplementedError


class BaseLiquidbRevertCommand(BaseLiquidbCommand, metaclass=ABCMeta):

    @staticmethod
    def _get_applied_snapshot():
        """Return latest applied snapshot by id"""
        try:
            latest = Snapshot.objects.filter(applied=True).latest('id')
        except ObjectDoesNotExist as error:
            raise CommandError('No latest snapshot present') from error
        return latest

    def _revert_to_snapshot(self, snapshot: Snapshot):
        """Revert db state to given snapshot"""
        targets = snapshot.migrations.values_list('app', 'name')
        if not targets:
            # snapshot that do not have any migrations
            # TODO get all apps from django apps and migrate everything to zero ?
            raise CommandError(
                f'No connected migrations found for snapshot {snapshot.name}'
            )
        executor = MigrationExecutor(self.connection)
        try:
            _: ProjectState = executor.migrate(targets)
        except KeyError:
            message = (
                '\n'.join(
                    [
                        f'* App Name: {app} ; Migration: {migration}'
                        for app, migration in targets
                    ]
                )
            )
            raise CommandError(
                f'\nSome migrations are missing.\n'
                f'Please make sure all migrations in snapshot: "{snapshot.name}";\n'
                f'Are present in corresponding apps: \n{message}'
            )

    def _checkout_snapshot(self, snapshot: Snapshot, force=False):
        """Run all checks before reverting to desired state"""
        latest = self._get_applied_snapshot()
        consistent_with_migration_table = latest.consistent_state
        if not consistent_with_migration_table and not force:
            raise CommandError(
                'Migration state is inconsistent latest applied '
                'snapshot do not has all currently applied migrations. '
                'Please use --force flag to checkout anyway.'
            )
        if not consistent_with_migration_table:
            self.stdout.write('Force to apply migration. Unsaved changes will be dropped')

        # eq is not same as equal snapshot.id == latest.id
        # see liquidb.models.Snapshot.__eq__
        if snapshot == latest:
            # migration hashes are the same
            # nothing to do
            self.stdout.write(f'Snapshot "{latest.name}" already applied ')
            sys.exit(0)
        self._revert_to_snapshot(snapshot)
        with transaction.atomic():
            latest.applied = False
            latest.save(update_fields=['applied'])

            snapshot.applied = True
            snapshot.save(update_fields=['applied'])

        self.stdout.write(f'Checkout from snapshot "{latest.name}" to "{snapshot.name}"')

    @abstractmethod
    def _handle(self, *args, **options):
        raise NotImplementedError
