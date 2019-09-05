from rest_framework import serializers
from rest_framework import viewsets

from django.db.models import Q, Prefetch

from mds import models

from datetime import datetime
import pytz


class ComplianceSerializer(serializers.ModelSerializer):
    rules_id = serializers.SerializerMethodField()

    compliances = serializers.SerializerMethodField()

    class Meta:
        model = models.Policy
        fields = ("id", "rules_id", "compliances")

    def get_rules_id(self, policy):
        rules = []
        for rule in policy.rules:
            rules.append(rule["rule_id"])
        return rules

    def get_compliances(self, policy):
        final_compliance = []
        for compliance in policy.compliances_pref:
            for current_compliance in final_compliance:
                if current_compliance["rule_id"] == compliance.rule:
                    for match in current_compliance["matches"]:
                        if match["geography"] == str(compliance.geography):
                            match["measured"] += 1
                            break
                    else:
                        current_compliance["matches"].append(
                            {"geography": str(compliance.geography), "measured": 1}
                        )
                    current_compliance["vehicles_in_violation"].append(
                        str(compliance.vehicle.id)
                    )
                    current_compliance["total_violations"] = len(
                        current_compliance["vehicles_in_violation"]
                    )
                    break
            else:
                final_compliance.append(
                    {
                        "rule_id": compliance.rule,
                        "matches": [
                            {"geography": str(compliance.geography), "measured": 1}
                        ],
                        "vehicles_in_violation": [str(compliance.vehicle.id)],
                        "total_violations": 1,
                    }
                )
        return final_compliance


class ComplianceViewSet(viewsets.ModelViewSet):
    queryset = models.Policy.objects
    serializer_class = ComplianceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        provider_id = self.request.GET.get("provider_id")
        end_date = self.request.GET.get("end_date")
        if end_date:
            end_date = datetime.fromtimestamp(int(end_date), tz=pytz.UTC)
        if provider_id and end_date:
            queryset = queryset.filter(
                Q(compliances__end_date__gte=end_date)
                | Q(compliances__end_date__isnull=True),
                compliances__vehicle__provider__id=provider_id,
                compliances__start_date__lte=end_date,
            ).prefetch_related(
                Prefetch(
                    "compliances",
                    queryset=models.Compliance.objects.filter(
                        Q(end_date__gte=end_date) | Q(end_date__isnull=True),
                        vehicle__provider__id=provider_id,
                        start_date__lt=end_date,
                    ),
                    to_attr="compliances_pref",
                )
            )
        elif provider_id:
            queryset = queryset.filter(
                compliances__vehicle__provider__id=provider_id
            ).prefetch_related(
                Prefetch(
                    "compliances",
                    queryset=models.Compliance.objects.filter(
                        vehicle__provider__id=provider_id
                    ),
                    to_attr="compliances_pref",
                )
            )
        elif end_date:
            queryset = queryset.filter(
                Q(compliances__end_date__gte=end_date)
                | Q(compliances__end_date__isnull=True),
                compliances__start_date__lte=end_date,
            ).prefetch_related(
                Prefetch(
                    "compliances",
                    queryset=models.Compliance.objects.filter(),
                    to_attr="compliances_pref",
                )
            )
        else:
            queryset = queryset.prefetch_related(
                Prefetch(
                    "compliances",
                    queryset=models.Compliance.objects.filter(),
                    to_attr="compliances_pref",
                )
            )

        return queryset
