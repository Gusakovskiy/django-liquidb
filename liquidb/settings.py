import os

from django.conf import settings

ADMIN_SNAPSHOT_ACTIONS = os.environ.get("ADMIN_SNAPSHOT_ACTIONS")
if ADMIN_SNAPSHOT_ACTIONS is None:
    ADMIN_SNAPSHOT_ACTIONS = getattr(settings, "ADMIN_SNAPSHOT_ACTIONS", True)
