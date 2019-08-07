from mds.provider_mapping import (
    PROVIDER_REASON_TO_AGENCY_EVENT,
    AGENCY_EVENT_TO_PROVIDER_REASON,
)


def test_provider_agency_mapping():
    """
    Checks that the bidirectional mappings are kind of consistent
    """
    for provider_reason, agency_event in PROVIDER_REASON_TO_AGENCY_EVENT.items():
        assert AGENCY_EVENT_TO_PROVIDER_REASON[agency_event] == provider_reason
