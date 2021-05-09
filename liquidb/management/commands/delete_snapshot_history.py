import sys

from django.db import transaction

from ._private import BaseLiquidbRevertCommand
from ...models import Snapshot


class Command(BaseLiquidbRevertCommand):
    help = "Delete all history of snapshots"

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            action="store_false",
            dest="interactive",
            default=True,
            help="Do not ask for confirmation ",
        )

    def _handle(self, *args, **options):
        interactive = options["interactive"]
        if interactive:
            confirm = input(
                f"""
                You have requested to delete snapshot history with all migrations.
                This action is IRREVERSIBLE.
                Are you sure you want to do this?

                Type 'yes' to continue, or 'no' to cancel: """
            )
            if confirm != "yes":
                self.stdout.write("Snapshot history deletion is canceled")
                sys.exit(0)
        with transaction.atomic():
            _total, models = Snapshot.objects.all().delete()
            snapshots = models.get("liquidb.Snapshot", 0)
            migrations_states = models.get("liquidb.MigrationState", 0)
        self.stdout.write(
            f"Successfully deleted history of {snapshots} snapshots and {migrations_states} migrations"
        )
