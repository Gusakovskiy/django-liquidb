import hashlib
from typing import Tuple, List
from uuid import uuid4

from django.db import models, connection
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import Max, Index, Q
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.timezone import now

from liquidb.consts import SELF_NAME


def _generate_commit_name() -> str:
    """Generates commit name base on datetime"""
    date = now().strftime('%d-%m-%YT%H:%M:%S')
    salt = get_random_string(6)
    return f'{salt}_{date}'


def _create_migration_hash(migration_identifiers: List[Tuple[str, str]]) -> str:
    """create md5 out of tuples of [(app_name, migration_file), ...]"""
    separator = ';'
    inner_separator = '-'
    # always sort alphabetically to ensure same result for unsorted app and sorted
    joined_value = separator.join(inner_separator.join([app, name]) for app, name in sorted(migration_identifiers))
    # no reason to check it is only hash of commits
    return hashlib.md5(joined_value.encode('utf-8')).hexdigest()  # nosec  # NOQA


def get_latest_applied_migrations_qs(connection_obj=None) -> 'QuerySet[MigrationRecorder.Migration]':
    """Return latest applied migration in all django apps in project"""
    if connection_obj is None:
        connection_obj = connection
    recorder = MigrationRecorder(connection_obj)
    migration_qs = recorder.migration_qs.exclude(app=SELF_NAME)
    lastest_ids = migration_qs.values('app').annotate(
        latest_id=Max('id')
    ).values_list(
        'latest_id',
        flat=True,
    )
    return migration_qs.filter(id__in=lastest_ids)


class Snapshot(models.Model):
    name = models.TextField(default=_generate_commit_name, db_index=True, unique=True)
    created = models.DateTimeField(default=now)
    applied = models.BooleanField(default=False)

    class Meta:
        indexes = [
            # by default all applied is false
            # only one row can be applied at the time
            Index(fields=['applied'], name='unique_applied', condition=Q(applied=True))
        ]

    def __repr__(self):
        class_name = self.__class__.__name__
        return f'{class_name}: {self.id}, {self.name}'

    def __eq__(self, other):
        if not isinstance(other, Snapshot):
            return False
        return self.migration_hash == other.migration_hash

    def __hash__(self):
        return hash(self.migration_hash)

    @property
    def consistent_state(self) -> bool:
        """Return True if all connected migrations to current snapshot is applied"""
        current_state = get_latest_applied_migrations_qs().values_list('app', 'name')
        current_hash = _create_migration_hash(current_state)
        return self.migration_hash == current_hash

    @cached_property
    def migration_hash(self) -> str:
        """Generate migration hash"""
        return _create_migration_hash(self.migrations.values_list('app', 'name'))


class MigrationState(models.Model):
    uuid = models.UUIDField(unique=True, primary_key=True, db_index=True, default=uuid4)
    snapshot = models.ForeignKey(Snapshot, on_delete=models.CASCADE, related_name='migrations')
    migration_id = models.IntegerField(db_index=True)
    # redundant info to restore migration
    # from django/db/migrations/recorder.py:30
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)

    def __repr__(self):
        return f'Migration {self.app} {self.name}'
