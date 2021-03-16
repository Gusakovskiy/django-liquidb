import pytest
from django.core.management import call_command, CommandError

from liquidb.models import Snapshot


@pytest.mark.django_db
def test_delete_snapshot_by_name_applied(create_migration_state_fixture):
    apps = [('first_app', '0001'), ('second_app', '0002'), ('third_app', '0003')]
    create_migration_state_fixture(apps)
    snapshot_name = 'init'
    call_command('create_migration_snapshot', name=snapshot_name)
    with pytest.raises(CommandError):
        call_command('delete_snapshot_by_name', name=snapshot_name, interactive=False)
    assert Snapshot.objects.count() == 1


@pytest.mark.django_db
def test_delete_snapshot_by_name_not_applied(create_migration_state_fixture):
    apps = [('first_app', '0001'), ('second_app', '0002'), ('third_app', '0003')]
    create_migration_state_fixture(apps)
    snapshot_name = 'first'
    call_command('create_migration_snapshot', name=snapshot_name)
    apps = [('first_app', '0002'), ('second_app', '0003'), ('third_app', '0004')]
    create_migration_state_fixture(apps)
    call_command('create_migration_snapshot', name='second')
    call_command('delete_snapshot_by_name', name=snapshot_name, interactive=False)
    assert Snapshot.objects.count() == 1
    snapshot = Snapshot.objects.first()
    assert snapshot.applied is True
    assert snapshot.consistent_state is True
