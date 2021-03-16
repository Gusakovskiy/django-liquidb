import pytest
from liquidb.models import get_latest_applied_migrations_qs

_EXPECTED_APPS = [
    ('first_app', '0001'),
    ('second_app', '0003'),
    ('third_app', '0005'),
]


@pytest.fixture(scope='function')
def _create_apps_fixture(create_migration_state_fixture):
    create_migration_state_fixture(_EXPECTED_APPS)


@pytest.mark.django_db
@pytest.mark.usefixtures('_create_apps_fixture')
def test_latest_applied_migrations_qs():
    ids = get_latest_applied_migrations_qs()
    assert ids.count() == 3
    assert set(ids.values_list('app', flat=True)) == set([app_name for app_name, _ in _EXPECTED_APPS])
    assert set(ids.values_list('name', flat=True)) == set([migration_name for _, migration_name in _EXPECTED_APPS])
