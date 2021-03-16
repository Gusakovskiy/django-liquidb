from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder


def change_state_mock(self, snapshot):  # pylint: disable=unused-argument
    # unfortunately no other way that we can chane state in tests
    # without all migrations files and whole django machinery
    # so for this test we will mock this state
    recorder = MigrationRecorder(connection=connection)
    Migration = recorder.Migration
    migration_state = snapshot.migrations.values_list('app', 'name')
    with transaction.atomic():
        Migration.objects.all().delete()
        for app, name in migration_state:
            m = Migration(
                app=app,
                name=name,
            )
            m.save()