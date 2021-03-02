import hashlib
from typing import Tuple, List

from django.db import models
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.timezone import now
from uuid import uuid4


def _generate_commit_name():
    date = now().strftime('%d-%m-%YT%H:%M:%S')
    salt = get_random_string(6)
    return f'{salt}_{date}'


def create_migration_hash(migration_identifiers: List[Tuple[str, str]]) -> str:
    separator = ';'
    inner_separator = '-'
    # always sort alphabetically to ensure same result for unsorted app and sorted
    joined_value = separator.join(inner_separator.join([app, name]) for app, name in sorted(migration_identifiers))
    return hashlib.md5(joined_value.encode('utf-8')).hexdigest()


class Snapshot(models.Model):
    name = models.TextField(default=_generate_commit_name, db_index=True, unique=True)
    created = models.DateTimeField(default=now)
    applied = models.BooleanField(default=True)

    def __repr__(self):
        class_name = self.__class__.__name__
        return f'{class_name}: {self.id}, {self.name}'

    @cached_property
    def migration_hash(self):
        return create_migration_hash(self.migrations.values_list('app', 'name'))


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
