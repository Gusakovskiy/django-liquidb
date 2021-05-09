import sys

from django.core.management import CommandError

from ._private import BaseLiquidbCommand
from ...db_tools import SnapshotCreationHandler, SnapshotHandlerException


class Command(BaseLiquidbCommand):
    help = "Create snapshot of migration state."

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            type=str,
            help="Verbose name of snapshot",
        )
        parser.add_argument(
            "--overwrite",
            type=int,
            default=0,
            choices=[0, 1],
            help="If snapshot with given name exist it will overwrite it",
        )

    def _handle(self, *args, **options):
        snapshot_name = options["name"]
        handler = SnapshotCreationHandler(snapshot_name, bool(options["overwrite"]))
        try:
            created = handler.create()
        except SnapshotHandlerException as e:
            raise CommandError(e.error)
        if not created:
            self.stdout.write(
                "All migrations saved in currently applied snapshot. Nothing to create"
            )
            sys.exit(0)
        self.stdout.write(f'Snapshot "{snapshot_name}" successfully save')
