import pytest
from django.core.management import call_command

from liquidb.models import Snapshot


@pytest.mark.django_db
@pytest.mark.parametrize(
    'apps', [
        pytest.param(
            [('first_app', '0001'), ('second_app', '0002'), ('third_app', '0003')],
            id='Few apps '
        ),
        pytest.param(
            [],
            id='Empty migration state',
        )
    ]
)
def test_delete_snapshot_history(apps, create_migration_state_fixture):
    create_migration_state_fixture(apps)
    call_command('create_migration_snapshot', name='init')
    call_command('delete_snapshot_history', interactive=False)
    assert Snapshot.objects.count() == 0
