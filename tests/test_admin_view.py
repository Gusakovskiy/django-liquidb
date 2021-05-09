from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from liquidb.db_tools import SnapshotCheckoutHandler
from liquidb.models import Snapshot
from tests.tools_tests import change_state_mock


def _reverse_snapshot_change(obj):
    return reverse("admin:liquidb_snapshot_change", args=(obj.pk,))


def _inject_managment_form_values(data):
    managment_form_data = {
        "migrations-TOTAL_FORMS": 1,
        "migrations-INITIAL_FORMS": 1,
    }
    data = {**data, **managment_form_data}
    return data


@pytest.fixture(scope="function")
def create_two_snapshots_fixture(create_snapshot_fixture):
    apps_1 = [("first_app", "0001"), ("second_app", "0005")]
    snapshot_one = create_snapshot_fixture(apps_1, "init")
    apps_2 = [("first_app", "0001"), ("second_app", "0006"), ("third_app", "0001")]
    snapshot_two = create_snapshot_fixture(apps_2, "second")
    return snapshot_one, snapshot_two


@pytest.mark.django_db
def test_changeview_snapshot_single(admin_client_fixture, create_snapshot_fixture):
    apps = [("first_app", "0001"), ("second_app", "0005")]
    snapshot = create_snapshot_fixture(apps, "init")
    client = admin_client_fixture
    response = client.get(_reverse_snapshot_change(snapshot))
    assert response.status_code == 200


@pytest.mark.django_db
def test_changeview_two_snapshots_check_not_applied(
    admin_client_fixture, create_two_snapshots_fixture
):
    client = admin_client_fixture
    snapshot_one, snapshot_two = create_two_snapshots_fixture
    snapshot_one.refresh_from_db()
    assert snapshot_one.applied is False
    # not applied snapshot
    response = client.get(_reverse_snapshot_change(snapshot_one))
    assert response.status_code == 200
    soup = BeautifulSoup(response.rendered_content, "html.parser")
    apply_buttons = soup.find_all("div", class_="form-row field-snapshot_actions")
    # assert it is only one button
    assert len(apply_buttons) == 1
    assert apply_buttons[0].a.text == "Apply Snapshot"


@pytest.mark.django_db
def test_changeview_two_snapshots_check_applied(
    admin_client_fixture, create_two_snapshots_fixture
):
    client = admin_client_fixture
    snapshot_one, snapshot_two = create_two_snapshots_fixture
    snapshot_two.refresh_from_db()
    assert snapshot_two.applied is True
    # not applied snapshot
    response = client.get(_reverse_snapshot_change(snapshot_two))
    assert response.status_code == 200
    soup = BeautifulSoup(response.rendered_content, "html.parser")
    apply_buttons = soup.find_all("div", class_="form-row field-snapshot_actions")
    # assert it is only one button
    assert len(apply_buttons) == 1
    # this snapshot already applied
    assert apply_buttons[0].a is None


@pytest.mark.django_db
def test_changelist_snapshot_empty(admin_client_fixture):
    client = admin_client_fixture
    url = reverse("admin:liquidb_snapshot_changelist")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_changelist_snapshot_not_empty(
    admin_client_fixture, create_migration_state_fixture, create_snapshot_fixture
):
    client = admin_client_fixture
    apps = [("first_app", "0001"), ("second_app", "0005")]
    _snapshot = create_snapshot_fixture(apps, "init")
    url = reverse("admin:liquidb_snapshot_changelist")
    response = client.get(url)
    assert response.status_code == 200

    soup = BeautifulSoup(response.rendered_content, "html.parser")
    assert len(soup.find_all("a", class_="addlink")) == 1


@pytest.mark.django_db
def test_changelist_snapshot_two_snapshots(
    admin_client_fixture, create_migration_state_fixture, create_two_snapshots_fixture
):
    client = admin_client_fixture
    snapshot_one, snapshot_two = create_two_snapshots_fixture
    url = reverse("admin:liquidb_snapshot_changelist")
    response = client.get(url)
    assert response.status_code == 200

    soup = BeautifulSoup(response.rendered_content, "html.parser")
    change_list = soup.find(id="result_list")
    assert len(change_list.find_all("th", class_="field-name")) == 2
    assert str(snapshot_two.id) in change_list.find_all("th", class_="field-name")[
        0
    ].a.get("href")
    assert str(snapshot_one.id) in change_list.find_all("th", class_="field-name")[
        1
    ].a.get("href")
    snapshot_one.refresh_from_db()
    assert snapshot_one.applied is False
    apply_buttons = soup.find_all("td", class_="field-snapshot_actions")
    # second is empty because it is already applied
    assert apply_buttons[0].a is None
    # get apply button for snapshot one
    apply_button = apply_buttons[-1]
    assert str(snapshot_one.id) in apply_button.a.get("href")


@pytest.mark.django_db
def test_create_init_snapshot(admin_client_fixture, create_migration_state_fixture):
    name = "init"
    create_migration_state_fixture([("third_app", "0001"), ("five_app", "0005")])
    client = admin_client_fixture
    response = client.post(
        reverse("admin:liquidb_snapshot_add"),
        _inject_managment_form_values({"name": name}),
        follow=True,
    )
    assert response.status_code == 200
    snapshot = Snapshot.objects.get(name=name)
    assert snapshot.applied is True
    assert snapshot.consistent_state is True


@pytest.mark.django_db
def test_create_snapshot_with_existing(
    admin_client_fixture, create_snapshot_fixture, create_migration_state_fixture
):
    create_snapshot_fixture([("third_app", "0002"), ("five_app", "0005")], "init")
    client = admin_client_fixture
    create_migration_state_fixture([("third_app", "0003"), ("five_app", "0006")])
    snapshot_name = "following"
    response = client.post(
        reverse("admin:liquidb_snapshot_add"),
        _inject_managment_form_values({"name": snapshot_name}),
        follow=True,
    )
    assert response.status_code == 200
    snapshot = Snapshot.objects.get(name=snapshot_name)
    assert snapshot.applied is True
    assert snapshot.consistent_state is True


@pytest.mark.django_db
def test_existing_snapshot(admin_client_fixture, create_snapshot_fixture):
    name = "init"
    create_snapshot_fixture([("third_app", "0001"), ("five_app", "0005")], name)
    client = admin_client_fixture
    response = client.post(
        reverse("admin:liquidb_snapshot_add"),
        _inject_managment_form_values({"name": name}),
        follow=True,
    )
    soup = BeautifulSoup(response.rendered_content, "html.parser")
    errors = soup.find("ul", class_="errorlist nonfield")
    assert f"Snapshot with given name {name} already exists" in errors.text


@pytest.mark.django_db
def test_consistent_state_snapshot(admin_client_fixture, create_snapshot_fixture):
    create_snapshot_fixture([("third_app", "0002"), ("five_app", "0005")], "init")
    client = admin_client_fixture
    response = client.post(
        reverse("admin:liquidb_snapshot_add"),
        _inject_managment_form_values({"name": "second"}),
        follow=True,
    )
    soup = BeautifulSoup(response.rendered_content, "html.parser")
    errors = soup.find("ul", class_="errorlist nonfield")
    assert (
        "All migrations saved in currently applied snapshot. Nothing to create"
        in errors.text
    )


@pytest.mark.django_db
@patch.object(
    SnapshotCheckoutHandler,
    "_checkout_to_snapshot",
    new=change_state_mock,
)
def test_apply_snapshot(
    admin_client_fixture, create_two_snapshots_fixture, create_migration_state_fixture
):
    snapshot_1, snapshot_2 = create_two_snapshots_fixture
    client = admin_client_fixture
    snapshot_1.refresh_from_db()
    assert snapshot_1.applied is False
    response = client.post(
        reverse("admin:apply_snapshot", args=(snapshot_1.pk,)), follow=True
    )
    assert response.status_code == 200
    # check that first snapshot is applied
    snapshot_1.refresh_from_db()
    assert snapshot_1.consistent_state is True
    assert snapshot_1.applied is True
    # check that second snapshot is not applied
    snapshot_2.refresh_from_db()
    assert snapshot_2.applied is False
    assert snapshot_2.consistent_state is False
