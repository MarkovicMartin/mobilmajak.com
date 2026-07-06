from rest_framework import serializers

from .models import DailyDutyTemplate


class DailyDutyTemplateSerializer(serializers.ModelSerializer):
    periodicity_display = serializers.CharField(source='get_periodicity_display', read_only=True)

    class Meta:
        model = DailyDutyTemplate
        fields = [
            'id', 'title', 'description', 'periodicity', 'periodicity_display',
            'store', 'role', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
