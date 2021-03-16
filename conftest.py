import pytest
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # Disable constraints for SQLLite
        connection.disable_constraint_checking()


@pytest.fixture(scope='function')
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
