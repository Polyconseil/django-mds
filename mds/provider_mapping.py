from mds.enums import EVENT_TYPE

# Mappings between Provider and Agency
#
# When we poll providers (with provider API) we cast the event reason
# with PROVIDER_REASON_TO_AGENCY_EVENT because enums don't match
# and we use Agency API nomenclature
# Then when we are ourselves polled we use AGENCY_EVENT_TO_PROVIDER_REASON
# and PROVIDER_REASON_TO_PROVIDER_EVENT_TYPE to be compliant
# with Provider API nomenclature

# Converts a Provider event_type_reason to an Agency event
PROVIDER_REASON_TO_AGENCY_EVENT = {
    "service_start": EVENT_TYPE.service_start.name,
    "user_drop_off": EVENT_TYPE.trip_end.name,
    "rebalance_drop_off": EVENT_TYPE.rebalance_drop_off.name,
    "maintenance_drop_off": EVENT_TYPE.maintenance_drop_off.name,
    # TODO when updating Agency API
    # "agency_drop_off": EVENT_TYPE.XXX.name
    "user_pick_up": EVENT_TYPE.trip_start.name,
    "maintenance": EVENT_TYPE.maintenance.name,
    "low_battery": EVENT_TYPE.low_battery.name,
    "service_end": EVENT_TYPE.service_end.name,
    "rebalance_pick_up": EVENT_TYPE.rebalance_pick_up.name,
    "maintenance_pick_up": EVENT_TYPE.maintenance_pick_up.name,
    # TODO when updating Agency API
    # "agency_pick_up": EVENT_TYPE.XXX.name
}

# Converts an Agency event to a Provider event_type_reason
# Try to stay consistent with
# https://github.com/CityOfLosAngeles/mds-core/blob/master/packages/mds-provider/utils.ts
AGENCY_EVENT_TO_PROVIDER_REASON = {
    EVENT_TYPE.service_start.name: "service_start",
    EVENT_TYPE.cancel_reservation.name: "user_drop_off",
    EVENT_TYPE.trip_end.name: "user_drop_off",
    EVENT_TYPE.rebalance_drop_off.name: "rebalance_drop_off",
    EVENT_TYPE.maintenance_drop_off.name: "maintenance_drop_off",
    EVENT_TYPE.battery_charged.name: "maintenance_drop_off",
    EVENT_TYPE.reserve.name: "user_pick_up",
    EVENT_TYPE.trip_start.name: "user_pick_up",
    EVENT_TYPE.trip_enter.name: "user_pick_up",
    EVENT_TYPE.trip_leave.name: "user_pick_up",  # This is on really bad...
    EVENT_TYPE.low_battery.name: "low_battery",
    EVENT_TYPE.maintenance.name: "maintenance",
    EVENT_TYPE.deregister.name: "service_end",
    EVENT_TYPE.service_end.name: "service_end",
    EVENT_TYPE.register.name: "service_end",
    EVENT_TYPE.rebalance_pick_up.name: "rebalance_pick_up",
    EVENT_TYPE.maintenance_pick_up.name: "maintenance_pick_up",
}

# Inside the Provider API, maps the event_type_reason to the corresponding event_type
PROVIDER_REASON_TO_PROVIDER_EVENT_TYPE = {
    "service_start": "available",
    "user_drop_off": "available",
    "rebalance_drop_off": "available",
    "maintenance_drop_off": "available",
    "agency_drop_off": "available",  # Doesn't exist in agency yet
    "user_pick_up": "reserved",
    "low_battery": "unavailable",
    "maintenance": "unavailable",
    "service_end": "removed",
    "rebalance_pick_up": "removed",
    "maintenance_pick_up": "removed",
    "agency_pick_up": "removed",  # Doesn't exist in agency yet
}
