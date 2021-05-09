from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, connection
from django.db.migrations.exceptions import NodeNotFoundError
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import ProjectState

from liquidb.models import Snapshot, MigrationState, get_latest_applied_migrations_qs


class SnapshotHandlerException(Exception):
    def __init__(self, error):
        self.error = error
        super().__init__()


class SnapshotCheckoutHandler:
    def __init__(self, snapshot: Snapshot, output=None):
        self.snapshot = snapshot
        self.output = output

    def _write_to_output(self, message):
        """Helper function to wirte to output if specified"""
        if self.output is not None:
            self.output.write(message)

    def _applied_queryset(self):
        return Snapshot.objects.filter(applied=True)

    def _get_lastest_applied_snapshot(self):
        """Return latest applied snapshot by id"""
        try:
            latest = self._applied_queryset().latest("id")
        except ObjectDoesNotExist as error:
            raise SnapshotHandlerException("No latest snapshot present") from error
        return latest

    def _checkout_to_snapshot(self, snapshot: Snapshot):
        """Revert db state to given snapshot"""
        targets = snapshot.migrations.values_list("app", "name")
        if not targets:
            # snapshot that do not have any migrations
            # TODO get all apps from django apps and migrate everything to zero ?
            raise SnapshotHandlerException(
                f"No connected migrations found for snapshot {snapshot.name}"
            )
        executor = MigrationExecutor(connection)
        try:
            _: ProjectState = executor.migrate(targets)
        except KeyError:
            # TODO check exact migration that missing
            message = "\n".join(
                [
                    f"* App Name: {app} ; Migration: {migration}"
                    for app, migration in targets
                ]
            )
            raise SnapshotHandlerException(
                f"\nSome migrations are missing.\n"
                f'Please make sure all migrations in snapshot: "{snapshot.name}";\n'
                f"Are present in corresponding apps: \n{message}"
            )
        except NodeNotFoundError as error:
            raise SnapshotHandlerException(error.message)

    @property
    def applied_snapshot_exists(self):
        return self._applied_queryset().exists()

    def checkout(self, force=False):
        latest = self._get_lastest_applied_snapshot()
        consistent_with_migration_table = latest.consistent_state
        if not consistent_with_migration_table and not force:
            raise SnapshotHandlerException(
                "Migration state is inconsistent latest applied "
                "snapshot do not has all currently applied migrations. "
                "Please use --force flag to checkout anyway."
            )
        if not consistent_with_migration_table:
            self._write_to_output(
                "Force to apply migration. Unsaved changes will be dropped"
            )

        # eq is not same as equal snapshot.id == latest.id
        # see liquidb.models.Snapshot.__eq__
        if self.snapshot == latest:
            # migration hashes are the same
            # nothing to do
            self._write_to_output(f'Snapshot "{latest.name}" already applied ')
            return

        self._checkout_to_snapshot(self.snapshot)
        with transaction.atomic():
            latest.applied = False
            latest.save(update_fields=["applied"])

            self.snapshot.applied = True
            self.snapshot.save(update_fields=["applied"])
        self._write_to_output(
            f'Checkout from snapshot "{latest.name}" to "{self.snapshot.name}"'
        )


class SnapshotCreationHandler:  # pylint: disable=too-few-public-methods
    def __init__(self, snapshot_name, overwrite):
        self.snapshot_name = snapshot_name
        self.overwrite = overwrite
        self.snapshot = None

    def _create(
        self,
        snapshot,
        latest,
    ):
        with transaction.atomic():
            if latest is not None:
                latest.applied = False
                latest.save(update_fields=["applied"])
            migrations = get_latest_applied_migrations_qs(connection).only(
                "id", "app", "name"
            )
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
            MigrationState.objects.bulk_create(
                to_create, batch_size=1000, ignore_conflicts=True
            )

    def create(self, dry_run=False) -> bool:
        exists = Snapshot.objects.filter(name=self.snapshot_name).exists()
        if exists and not self.overwrite:
            raise SnapshotHandlerException(
                f"Snapshot with given name {self.snapshot_name} already exists.\n",
            )

        if exists:
            snapshot = Snapshot.objects.get(name=self.snapshot_name)
        else:
            snapshot = Snapshot(name=self.snapshot_name)

        latest = Snapshot.objects.filter(applied=True).last()
        if latest is not None and latest.consistent_state:
            return False
        if dry_run:
            return True

        self._create(snapshot, latest)
        self.snapshot = snapshot
        return True
