from rest_framework import serializers

from .models import WreckPart


def normalize_store(value):
    store = (value or '').strip()
    if not store or store == 'Neuvedeno':
        return 'Globus'
    return store


class WreckPartSerializer(serializers.ModelSerializer):
    class Meta:
        model = WreckPart
        fields = [
            'id', 'model_name', 'part_type', 'quantity', 'store',
            'notes', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_store(self, value):
        return normalize_store(value)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['store'] = normalize_store(data.get('store'))
        return data
