from rest_framework import serializers
from .models import Ukol


class UkolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ukol
        fields = [
            "id",
            "ukol",
            "priorita",
            "deadline",
            "stav",
            "id_prodejce_ukol",
            "id_prodejce_zadal",
            "id_prodejny",
            "vytvoreno",
            "upraveno",
        ]


