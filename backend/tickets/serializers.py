from rest_framework import serializers
from .models import Ticket, TicketImage, TicketComment


class TicketImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketImage
        fields = ['id', 'obrazek', 'nahrano']


class TicketCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketComment
        fields = ['id', 'autor_id', 'autor_jmeno', 'text', 'vytvoreno', 'upraveno']


class TicketSerializer(serializers.ModelSerializer):
    images = TicketImageSerializer(many=True, read_only=True)
    comments = TicketCommentSerializer(many=True, read_only=True)
    stav_display = serializers.CharField(source='get_stav_display', read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'nazev', 'popis', 'stav', 'stav_display',
            'autor_id', 'autor_jmeno', 'url', 'opraveno_at', 'vytvoreno', 'upraveno',
            'images', 'comments',
        ]


class TicketListSerializer(serializers.ModelSerializer):
    """Odlehčená verze bez komentářů pro seznam."""
    stav_display = serializers.CharField(source='get_stav_display', read_only=True)
    images = TicketImageSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'nazev', 'popis', 'stav', 'stav_display',
            'autor_id', 'autor_jmeno', 'url', 'opraveno_at', 'vytvoreno', 'upraveno', 'images',
        ]
