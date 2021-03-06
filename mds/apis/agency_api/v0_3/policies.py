from rest_framework import serializers
from rest_framework import viewsets

from django.db.models import Q
from django.db.models.functions import Now

from mds import enums
from mds import models
from mds import utils
from mds.apis import utils as apis_utils


class RuleSerializer(serializers.Serializer):
    name = serializers.CharField(help_text="Name of rule")
    rule_type = serializers.CharField(help_text="Type of policy (see Rule Types)")
    geographies = serializers.ListField(
        child=serializers.UUIDField(),
        help_text=(
            "List of Geography UUIDs (non-overlapping) "
            "specifying the covered geography"
        ),
    )
    statuses = serializers.DictField(
        help_text=(
            "Vehicle statuses to which this rule applies. "
            "Optionally, you may provide specific event_type's for the rule "
            "to apply to as a subset of a given status. "
            'An empty list or null/absent defaults to "all".'
        )
    )
    rule_units = serializers.CharField(
        required=False, help_text="Measured units of policy (see Rule Units)"
    )
    vehicle_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text='Applicable vehicle types, default "all".',
    )
    propulsion_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text='Applicable vehicle propulsion types, default "all".',
    )
    minimum = serializers.IntegerField(
        required=False, help_text="Minimum value, if applicable (default 0)"
    )
    maximum = serializers.IntegerField(
        required=False, help_text="Maximum value, if applicable (default unlimited)"
    )
    start_time = serializers.TimeField(
        required=False,
        help_text=(
            "Beginning time-of-day when the rule is in effect (default 00:00:00)."
        ),
    )
    end_time = serializers.TimeField(
        required=False,
        help_text="Ending time-of-day when the rule is in effect (default 23:59:59).",
    )
    days = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            'Days ["sun", "mon", "tue", "wed", "thu", "fri", "sat"] '
            "when the rule is in effect (default all)"
        ),
    )
    messages = serializers.DictField(
        required=False,
        help_text=(
            "Message to rider user, if desired, in various languages, "
            "keyed by language tag (see Messages)"
        ),
    )
    value_url = serializers.URLField(
        required=False,
        help_text=(
            "URL to an API endpoint that can provide dynamic information "
            "for the measured value (see Value URL)"
        ),
    )

    def to_representation(self, rule):
        # Some rule types are for internal use only
        # "permit" is an alias for "count" (fleet size)
        if rule["rule_type"] == "permit":
            rule = rule.copy()
            rule["rule_type"] = enums.POLICY_RULE_TYPES.count.name
        return rule


class PolicySerializer(serializers.Serializer):
    name = serializers.CharField(help_text="Name of policy")
    policy_id = serializers.UUIDField(source="id", help_text="Unique ID of policy")
    provider_ids = serializers.SerializerMethodField(
        help_text=(
            "Providers for whom this policy is applicable "
            "(null or absent implies all Providers)"
        )
    )
    description = serializers.CharField(help_text="Description of policy")
    start_date = apis_utils.UnixTimestampMilliseconds(
        help_text="Beginning date/time of policy enforcement"
    )
    end_date = apis_utils.UnixTimestampMilliseconds(
        help_text="End date/time of policy enforcement"
    )
    published_date = apis_utils.UnixTimestampMilliseconds(
        help_text="Timestamp that the policy was published"
    )
    prev_policies = serializers.SerializerMethodField(
        help_text="Unique IDs of prior policies replaced by this one"
    )
    rules = RuleSerializer(many=True, help_text="List of applicable rule elements")

    def get_provider_ids(self, policy):
        # Why we need a prefetch_related()!
        return [str(provider.id) for provider in policy.providers.all()]

    def get_prev_policies(self, policy):
        return [str(policy.id) for policy in policy.prev_policies.all()]


class PolicyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        models.Policy.objects.prefetch_related("providers", "prev_policies")
        .filter(published_date__isnull=False)  # Not drafts
        .order_by("start_date")
    )
    permission_classes = ()  # Public endpoint but results are restricted
    lookup_field = "id"
    serializer_class = PolicySerializer
    # TODO filter_backends

    def get_queryset(self):
        queryset = super().get_queryset()

        provider_id = getattr(self.request.user, "provider_id", None)
        if provider_id:
            # Filter for general-purpose policies,
            # or the ones written for this provider
            queryset = queryset.filter(
                Q(providers__isnull=True) | Q(providers=provider_id)
            )
            # The raw results will expose what other providers this policy applies to
            # Is this information leakage?
        else:
            # Only general-purpose policies to other users
            queryset = queryset.filter(providers__isnull=True)

        # Filter by date range
        start_time = self.request.GET.get("start_time")
        if start_time:
            start_time = utils.from_mds_timestamp(int(start_time))
        else:
            start_time = Now()
        range_q = Q(end_date__gt=start_time) | Q(end_date__isnull=True)

        end_time = self.request.GET.get("end_time")
        if end_time:
            end_time = utils.from_mds_timestamp(int(end_time))
            range_q &= Q(start_date__lte=end_time)

        queryset = queryset.filter(range_q)

        return queryset
