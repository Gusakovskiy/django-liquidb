import sys

from django.core.management import CommandError
from django.db import transaction

from ._private import BaseLiquidbRevertCommand


class Command(BaseLiquidbRevertCommand):
    help = 'Delete snapshot by name'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            help='Name of snapshot to delete',
        )
        parser.add_argument(
            '--noinput',
            action='store_false',
            dest='interactive',
            default=True,
            help='Do not ask for confirmation '
        )

    def _handle(self, *args, **options):
        name = options['name']
        interactive = options['interactive']
        snapshot = self.get_snapshot(name)
        if interactive:
            confirm = input(f"""
                You have requested to delete snapshot "{name}" with all migrations connected to it.
                This action is IRREVERSIBLE. 
                Are you sure you want to do this?
    
                Type 'yes' to continue, or 'no' to cancel: """
            )
            if confirm != 'yes':
                self.stdout.write('Snapshot deletion is canceled')
                sys.exit(0)

        if snapshot.applied:
            raise CommandError(f'Snapshot with name {name} is applied and couldn\'t be deleted')
        with transaction.atomic():
            _total, models = snapshot.delete()
            migrations_states = models.get('liquidb.MigrationState', 0)

        self.stdout.write(f'Successfully deleted snapshot "{name}" and {migrations_states} migrations')
