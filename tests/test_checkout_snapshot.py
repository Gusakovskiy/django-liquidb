from unittest.mock import patch

import pytest
from django.core.management import call_command
from liquidb.management.commands._private import BaseLiquidbRevertCommand  # NOQA # pylint: disable=protected-access
from liquidb.models import Snapshot
from tests.tools_tests import change_state_mock

_STATE_TEMPLATE = 'state_{}'


@pytest.fixture(scope='function')
def _create_three_state_fixture(create_migration_state_fixture):
    state_template = [('first_app', '000{}'), ('second_app', '000{}'), ('third_app', '000{}')]
    for counter in range(1, 4):
        state = [
            (app_name, migration.format(counter))
            for app_name, migration in state_template
        ]
        create_migration_state_fixture(state)
        call_command('create_migration_snapshot', name=_STATE_TEMPLATE.format(counter))


@pytest.mark.django_db
@patch.object(
    BaseLiquidbRevertCommand,
    '_revert_to_snapshot',
    new=change_state_mock,
)
def test_checkout_between_snapshots(_create_three_state_fixture):
    state_1 = _STATE_TEMPLATE.format(1)
    state_2 = _STATE_TEMPLATE.format(2)
    state_3 = _STATE_TEMPLATE.format(3)
    call_command('checkout_snapshot', name=state_1)
    snapshot = Snapshot.objects.get(name=state_1)
    assert snapshot.consistent_state is True
    # state_3
    call_command('checkout_snapshot', name=state_3)
    snapshot = Snapshot.objects.get(name=state_3)
    assert snapshot.consistent_state is True
    # state_2
    call_command('checkout_snapshot', name=state_2)
    snapshot = Snapshot.objects.get(name=state_2)
    assert snapshot.consistent_state is True
