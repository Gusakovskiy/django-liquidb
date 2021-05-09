import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test import Client

from liquidb.db_tools import SnapshotCreationHandler, SnapshotHandlerException


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # Disable constraints for SQLLite
        connection.disable_constraint_checking()


@pytest.fixture(scope="function")
def create_migration_state_fixture(django_db_blocker):
    # from django.db.backends.sqlite3 import schema
    # from django.db.backends.sqlite3 import base
    def wrapper_fixture(test_migrations):
        recorder = MigrationRecorder(connection)
        Migration = recorder.Migration
        with django_db_blocker.unblock():
            table_exists = recorder.has_table()
            if not table_exists:
                with connection.schema_editor(atomic=False) as editor:
                    editor.create_model(recorder.Migration)

            for app, name in test_migrations:
                m = Migration(
                    app=app,
                    name=name,
                )
                m.save()

    return wrapper_fixture


@pytest.fixture(scope="function")
def admin_client_fixture(django_db_blocker):
    _user = User.objects.create_superuser(
        username="superuser", password="secret", email="admin@example.com"  # nosec
    )
    client = Client()
    client.login(username="superuser", password="secret")
    return client


@pytest.fixture(scope="function")
def create_empty_snapshot_fixture(django_db_blocker):
    def wrapper(name):
        with django_db_blocker.unblock():
            handler = SnapshotCreationHandler(
                name,
                False,
            )
            try:
                created = handler.create(dry_run=False)
            except SnapshotHandlerException as e:
                raise AssertionError(e.error)
            if not created:
                raise AssertionError(
                    "All migrations saved in currently applied snapshot. Nothing to create"
                )
        return handler.snapshot

    return wrapper


@pytest.fixture(scope="function")
def create_snapshot_fixture(
    create_migration_state_fixture, create_empty_snapshot_fixture
):
    def wrapper(migration_state, snapshot_name):
        create_migration_state_fixture(migration_state)
        snapshot = create_empty_snapshot_fixture(snapshot_name)
        return snapshot

    return wrapper
