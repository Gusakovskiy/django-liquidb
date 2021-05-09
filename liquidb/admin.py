from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.core.checks import messages
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from .db_tools import (
    SnapshotCheckoutHandler,
    SnapshotHandlerException,
    SnapshotCreationHandler,
)
from .models import Snapshot, MigrationState
from .settings import ADMIN_SNAPSHOT_ACTIONS


class SnapshotAdminModelForm(ModelForm):
    def _create_snapshot(self, name: str, dry_run: bool):  # pylint: disable=no-self-use
        handler = SnapshotCreationHandler(
            name,
            False,
        )
        try:
            created = handler.create(dry_run=dry_run)
        except SnapshotHandlerException as error:
            raise ValidationError(error.error, code="name")
        if not created:
            raise ValidationError(
                "All migrations saved in currently applied snapshot. Nothing to create",
                code="consistent_snapshot",
            )
        return handler.snapshot

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk is not None:
            # somehow we modify snapshot
            raise ValidationError(
                "Snapshot is immutable you can't modify it",
                code="immutable_snapshot",
            )
        self._create_snapshot(
            name=self.cleaned_data["name"],
            # Run full validation in SnapshotCreationHandler
            dry_run=True,
        )
        return cleaned_data

    def save(self, commit=True):
        return self._create_snapshot(
            name=self.cleaned_data["name"],
            dry_run=commit,
        )

    def save_m2m(self):  # pylint: disable=method-hidden
        # DO not save any model everything
        # should be done in transaction in
        # self._create_snapshot
        pass


class StateInline(admin.StackedInline):
    model = MigrationState
    can_delete = False
    fk_name = "snapshot"

    # <editor-fold desc="Should be always readonly">
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # </editor-fold>


@admin.register(Snapshot)
class SnapshotAdminView(ModelAdmin):

    form = SnapshotAdminModelForm
    readonly_fields = (
        "created",
        "applied",
        "snapshot_actions",
    )
    list_display = (
        "name",
        "applied",
        "snapshot_actions",
    )
    inlines = [
        StateInline,
    ]

    # <editor-fold desc="Only View Permissions">
    # User should create and delete snapshots through cli
    def has_add_permission(self, request):
        return ADMIN_SNAPSHOT_ACTIONS

    def has_change_permission(self, request, obj=None):
        # never allow edit created snapshot
        return False

    def has_delete_permission(self, request, obj=None):
        return (
            ADMIN_SNAPSHOT_ACTIONS
            and
            # allow delete existing not applied snapshot
            obj is not None
            and not obj.applied
        )

    # </editor-fold>

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = []
        if ADMIN_SNAPSHOT_ACTIONS:
            custom_urls.append(
                url(
                    r"^(?P<snapshot_id>.+)/apply/$",
                    self.admin_site.admin_view(self.apply_snapshot),
                    name="apply_snapshot",
                )
            )
        return custom_urls + urls

    def snapshot_actions(self, obj):
        if ADMIN_SNAPSHOT_ACTIONS and obj.pk is not None and not obj.applied:
            return format_html(
                '<a class="button" href="{}">Apply Snapshot</a>&nbsp;',
                reverse("admin:apply_snapshot", args=[obj.pk]),
            )
        return ""

    snapshot_actions.short_description = "Snapshot Actions"
    snapshot_actions.allow_tags = True

    def apply_snapshot(
        self, request, snapshot_id, *args, **kwargs
    ):  # pylint: disable=unused-argument
        snapshot = self.get_object(request, snapshot_id)
        reversed_url = reverse(
            "admin:liquidb_snapshot_change",
            args=[snapshot.pk],
            current_app=self.admin_site.name,
        )
        handler = SnapshotCheckoutHandler(snapshot)
        if not handler.applied_snapshot_exists:
            self.message_user(
                request,
                "No applied snapshot present",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(reversed_url)

        try:
            # TODO change to apply without force True
            handler.checkout(force=True)
        except SnapshotHandlerException as e:
            self.message_user(
                request,
                e.error,
                level=messages.ERROR,
            )
            return HttpResponseRedirect(reversed_url)

        self.message_user(request, f"Successfully applied {snapshot.name}")
        return HttpResponseRedirect(reversed_url)

    def delete_model(self, request, obj=None):
        # delete snapshot and all related MigrationState
        super().delete_model(request, obj)
