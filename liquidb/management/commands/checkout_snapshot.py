from ._private import BaseLiquidbRevertCommand


class Command(BaseLiquidbRevertCommand):
    help = 'Revert migration state to given commit (snapshot)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            help='Name of snapshot to apply',
        )
        parser.add_argument(
            '--force',
            type=int,
            default=0,
            choices=[0, 1],
            help='Drop unsaved changes',
        )

    def _handle(self, *args, **options):
        snapshot = self.get_snapshot(options['name'])
        self._checkout_snapshot(snapshot, force=bool(options['force']))
