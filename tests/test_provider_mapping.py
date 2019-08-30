import pytest

from mds import enums, factories
from mds.provider_mapping import (
    AGENCY_EVENT_TO_PROVIDER_REASON,
    OLD_AGENCY_EVENT_TO_PROVIDER_REASON,
    OLD_PROVIDER_REASON_TO_AGENCY_EVENT,
    PROVIDER_REASON_TO_AGENCY_EVENT,
    OLD_TO_NEW_AGENCY_EVENT,
    get_new_event_from_old,
    get_old_event_from_new,
    get_provider_reason_from_both_mappings,
    get_same_mapping_event,
)


# This file tests the different functions of this old and new mapping:
# Old:
# Provider    --old_p_a-->    Agency    --old_a_p-->    Provider
# New:                   --old_to_new_a--
# Provider    --new_p_a-->    Agency    --new_a_p-->    Provider


def test_provider_agency_mapping():
    """
    Checks that the bidirectional mappings are kind of consistent.
    new_a_p ○ new_p_a = id
    """
    for provider_reason, agency_event in PROVIDER_REASON_TO_AGENCY_EVENT.items():
        assert AGENCY_EVENT_TO_PROVIDER_REASON[agency_event] == provider_reason


def test_old_provider_agency_mapping():
    """
    Checks that the old bidirectional mappings are kind of consistent
    old_a_p ○ old_p_a = id
    """
    for provider_reason, agency_event in OLD_PROVIDER_REASON_TO_AGENCY_EVENT.items():
        assert OLD_AGENCY_EVENT_TO_PROVIDER_REASON[agency_event] == provider_reason


def test_old_to_new_is_same_as_new():
    """
    Checks that when we apply the migration to the old events,
    we have the same result as with the new mappings.
    old_to_new_a ○ old_p_a = new_p_a
    """
    for reason, old_agency_event in OLD_PROVIDER_REASON_TO_AGENCY_EVENT.items():
        agency_event = get_new_event_from_old(old_agency_event)
        new_agency_event = PROVIDER_REASON_TO_AGENCY_EVENT[reason]
        assert agency_event == new_agency_event


def test_migration_new_idem():
    """
    Checks that when we apply the old_to_new migration to the new events,
    we don't change anything.
    old_to_new_a(new)= new
    """
    for _, agency_event in PROVIDER_REASON_TO_AGENCY_EVENT.items():
        new_agency_event = get_new_event_from_old(agency_event)
        assert agency_event == new_agency_event


def test_migration_idempotent():
    """
    Checks that applying the old to new mapping twice is the same as applying it once
    old_to_new_a ○ old_to_new_a = old_to_new_a
    """
    for _, agency_event in OLD_PROVIDER_REASON_TO_AGENCY_EVENT.items():
        new_agency_event = get_new_event_from_old(agency_event)
        new_new_agency_event = get_new_event_from_old(new_agency_event)
        assert new_agency_event == new_new_agency_event


def test_migration_reverse():
    """
    Checks that applying the reverse old_to_new mapping to the new events
    returns the old events.
    old_to_new_a ^-1 ○ old_to_new_a (old) = old
    """
    for old_event, _ in OLD_TO_NEW_AGENCY_EVENT.items():
        new_agency_event = get_new_event_from_old(old_event)
        old_agency_event = get_old_event_from_new(new_agency_event)
        assert old_agency_event == old_event


def test_migration_reverse_2():
    """
    Checks that applying the old_to_new mapping to the new event returns the new events.
    old_to_new_a ○ old_to_new_a ^-1 (new) = new
    """
    for _, new_event in OLD_TO_NEW_AGENCY_EVENT.items():
        old_agency_event = get_old_event_from_new(new_event)
        new_agency_event = get_new_event_from_old(old_agency_event)
        assert new_agency_event == new_event


def test_get_same_mapping_event():
    """
    Checks that the function to optimise the migration's performance returns
    the events that we do not want to update
    """
    assert get_same_mapping_event() == [
        ("service_start",),
        ("trip_end",),
        ("trip_start",),
        ("trip_enter",),
        ("cancel_reservation",),
        ("telemetry",),
        ("reserve",),
        ("deregister",),
        ("battery_charged",),
        ("trip_leave",),
        ("register",),
    ]


@pytest.fixture
def device():
    uuid1 = "aaaaaaa1-1342-413b-8e89-db802b2f83f6"
    provider = factories.Provider(name="Test provider")
    return factories.Device(
        id=uuid1,
        provider=provider,
        identification_number="1AAAAA",
        model="Testa_Model_S",
        category="car",
        propulsion=["combustion"],
        dn_status="available",
        dn_gps_point="Point(40 15.0)",
        dn_battery_pct=0.5,
    )


@pytest.mark.django_db
def test_get_provider_reason_from_both_mappings_old_objects(device):
    """
    Checks that the function to get the provider_reason from the EventRecord
    works as expected for old objects.
    """
    obj = factories.EventRecord(
        device=device,
        event_type=enums.PROVIDER_EVENT_TYPE_REASON.rebalance_drop_off.name,
    )
    provider_reason = get_provider_reason_from_both_mappings(obj)
    assert provider_reason in OLD_AGENCY_EVENT_TO_PROVIDER_REASON.values()
    assert provider_reason == enums.PROVIDER_EVENT_TYPE_REASON.rebalance_drop_off.name


@pytest.mark.django_db
def test_get_provider_reason_from_both_mappings_new_objects(device):
    """
    Checks that the function to get the provider_reason from the EventRecord
    works as expected for new objects.
    """
    obj = factories.EventRecord(
        device=device,
        event_type=enums.PROVIDER_EVENT_TYPE_REASON.service_end.name,
        event_type_reason=enums.EVENT_TYPE_REASON.maintenance.name,
    )
    provider_reason = get_provider_reason_from_both_mappings(obj)
    assert provider_reason in AGENCY_EVENT_TO_PROVIDER_REASON.values()
    assert provider_reason == enums.PROVIDER_EVENT_TYPE_REASON.maintenance.name


@pytest.mark.django_db
def test_get_provider_reason_from_both_mappings_new_objects_not_in_old(device):
    """
    Checks that the function to get the provider_reason from the EventRecord
    uses the old mapping for events that are not in the new mapping.
    """
    obj = factories.EventRecord(
        device=device,
        event_type=enums.PROVIDER_EVENT_TYPE_REASON.rebalance_pick_up.name,
    )
    provider_reason = get_provider_reason_from_both_mappings(obj)
    assert provider_reason in AGENCY_EVENT_TO_PROVIDER_REASON.values()
    assert provider_reason == enums.PROVIDER_EVENT_TYPE_REASON.rebalance_pick_up.name


@pytest.mark.django_db
def test_get_provider_reason_from_both_mappings_for_old_mapping(device):
    """
    Checks that the mapping are consistent for objects stored in the old format.
    """
    for reason, agency_event in OLD_PROVIDER_REASON_TO_AGENCY_EVENT.items():
        obj = factories.EventRecord(device=device, event_type=agency_event)
        provider_reason = get_provider_reason_from_both_mappings(obj)
        if agency_event == "service_end":
            # We skip this case because the old mapping is wrong for this one.
            # We want to map a Agency "service_end" to "maintenance"
            continue
        assert provider_reason == reason


@pytest.mark.django_db
def test_get_provider_reason_from_both_mappings_for_new_mapping(device):
    """
    Checks that the mapping are consistent for objects stored in the new format.
    """
    for reason, agency_event in PROVIDER_REASON_TO_AGENCY_EVENT.items():
        event_type, event_type_reason = (
            agency_event if len(agency_event) == 2 else agency_event + (None,)
        )
        obj = factories.EventRecord(
            device=device, event_type=event_type, event_type_reason=event_type_reason
        )
        provider_reason = get_provider_reason_from_both_mappings(obj)
        assert provider_reason == reason
