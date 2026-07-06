from rest_framework import serializers

from .models import WreckPart


class WreckPartSerializer(serializers.ModelSerializer):
    class Meta:
        model = WreckPart
        fields = [
            'id', 'model_name', 'part_type', 'quantity', 'store',
            'notes', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
