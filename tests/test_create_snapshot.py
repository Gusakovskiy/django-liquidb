from io import StringIO

import pytest
from django.core.management import call_command, CommandError
from liquidb.models import Snapshot
from mock import patch


@pytest.mark.django_db
@pytest.mark.parametrize(
    'apps', [
        pytest.param(
            [('first_app', '0001'), ('second_app', '0003'), ('third_app', '0005')],
            id='Three apps'
        ),
        pytest.param(
            [('first_app', '0001'), ('second_app', '0005')],
            id='Two apps'
        ),
        pytest.param(
            [('first_app', '0001')],
            id='Single app'
        ),
        pytest.param(
            [],
            id='Empty',
        )
    ]
)
def test_create_snapshot(apps, create_migration_state_fixture):
    expected = len(apps)
    create_migration_state_fixture(apps)
    s_name = 'init'
    call_command('create_migration_snapshot', name=s_name)
    assert Snapshot.objects.count() == 1
    snapshot = Snapshot.objects.first()
    assert snapshot.name == s_name
    assert snapshot.migrations.count() == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    'silent', [True, False]
)
def test_snapshot_already_exist(create_migration_state_fixture, silent):
    apps = [('first_app', '0001'), ('second_app', '0005')]
    snapshot_name = 'first'
    create_migration_state_fixture(apps)
    call_command('create_migration_snapshot', name=snapshot_name)
    if not silent:
        with pytest.raises(CommandError):
            call_command('create_migration_snapshot', name=snapshot_name, silent=silent)
    else:
        with pytest.raises(SystemExit):
            call_command('create_migration_snapshot', name=snapshot_name, silent=silent)


@pytest.mark.django_db
@patch('sys.stdout', new_callable=StringIO)
def test_snapshot_with_same_hash(patched_stdout, create_migration_state_fixture):
    apps = [('first_app', '0001'), ('second_app', '0005')]
    create_migration_state_fixture(apps)
    call_command('create_migration_snapshot', name='first')
    with pytest.raises(SystemExit):
        call_command('create_migration_snapshot', name='second')
    patched_stdout.assert_called_once_with('All migrations saved in currently applied snapshot. Nothing to create')


@pytest.mark.django_db
@patch('sys.stderr')
def test_snapshot_with_same_hash(patched_stderr, create_migration_state_fixture):
    first_state = [('first_app', '0001'), ('second_app', '0005')]
    create_migration_state_fixture(first_state)
    call_command('create_migration_snapshot', name='first')
    second_state = [('first_app', '0003'), ('third_app', '0001'), ('second_app', '0006')]
    create_migration_state_fixture(second_state)
    patched_stderr.assert_not_called()
