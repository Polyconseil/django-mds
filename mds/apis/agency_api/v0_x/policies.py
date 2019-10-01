from rest_framework import serializers
from rest_framework import viewsets

from django.db.models import Q
from django.db.models.functions import Now

from mds import models
from mds import utils
from mds.apis import utils as apis_utils


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
    rules = serializers.JSONField(help_text="List of applicable rule elements")

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
        range_q = Q(end_date__gte=start_time)

        end_time = self.request.GET.get("end_time")
        if end_time:
            end_time = utils.from_mds_timestamp(int(end_time))
            range_q &= Q(start_date__lte=end_time)

        queryset = queryset.filter(range_q)

        return queryset
