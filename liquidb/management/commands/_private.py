from abc import ABCMeta, abstractmethod

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

from ...db_tools import SnapshotCheckoutHandler, SnapshotHandlerException
from ...models import Snapshot, MigrationState, get_latest_applied_migrations_qs


class BaseLiquidbCommand(BaseCommand, metaclass=ABCMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = connection

    def _check_migration_db_exists(self):
        recorder = MigrationRecorder(self.connection)
        if not recorder.has_table():
            raise CommandError("No migration table present")

    def _check_liquidb_tables_exists(self):
        with self.connection.cursor() as cursor:
            tables = self.connection.introspection.table_names(cursor)
        tables_to_check = [
            Snapshot._meta.db_table,
            MigrationState._meta.db_table,
        ]  # NOQA
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
            raise CommandError(
                f'Snapshot with name: "{name}" doesn\'t exists'
            ) from error
        return snapshot

    @abstractmethod
    def _handle(self, *args, **options):
        raise NotImplementedError


class BaseLiquidbRevertCommand(BaseLiquidbCommand, metaclass=ABCMeta):
    def _checkout_snapshot(self, snapshot: Snapshot, force=False):
        """Run all checks before reverting to desired state"""

        handler = SnapshotCheckoutHandler(snapshot, self.stdout)
        if not handler.applied_snapshot_exists:
            raise CommandError("No latest snapshot present")

        try:
            handler.checkout(force=force)
        except SnapshotHandlerException as e:
            raise CommandError(e.error)

    @abstractmethod
    def _handle(self, *args, **options):
        raise NotImplementedError
