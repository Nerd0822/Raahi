from rest_framework import serializers

from .models import Plan, PlanItem


class PlanItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanItem
        fields = [
            "id",
            "plan",
            "category",
            "name",
            "notes",
            "time",
            "cost",
            "latitude",
            "longitude",
            "details",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A user may only file stops under their own plans.
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["plan"].queryset = Plan.objects.filter(user=request.user)


class PlanSerializer(serializers.ModelSerializer):
    items = PlanItemSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = [
            "id",
            "title",
            "destination",
            "start_date",
            "end_date",
            "status",
            "notes",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "End date can't be before the start date."}
            )
        return attrs
