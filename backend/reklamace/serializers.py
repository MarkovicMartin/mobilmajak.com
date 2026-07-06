from rest_framework import serializers

from .models import ReklamaceNotifikace, ReklamacePolozka, ReklamaceStatus, ZpusobVyrizeni
from .znacka import generate_nase_znacka


class ReklamacePolozkaSerializer(serializers.ModelSerializer):
    is_overdue = serializers.SerializerMethodField()
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    zpusob_vyrizeni_label = serializers.CharField(source='get_zpusob_vyrizeni_display', read_only=True)

    class Meta:
        model = ReklamacePolozka
        fields = [
            'id', 'nase_znacka', 'jejich_oznaceni', 'nazev_zbozi', 'dodavatel',
            'faktura', 'ean', 'p_kod', 'datum_odeslani', 'cislo_zasilky',
            'poznamka', 'prodejna', 'status', 'status_label', 'datum_vyrizeni',
            'zpusob_vyrizeni', 'zpusob_vyrizeni_label', 'odeslano_dodavateli_at',
            'sklad_vyskladneno', 'sklad_naskladneno', 'is_overdue', 'is_active',
            'created_by_id', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'nase_znacka', 'created_at', 'updated_at', 'odeslano_dodavateli_at',
            'is_overdue', 'status_label', 'zpusob_vyrizeni_label', 'status', 'created_by_id',
        ]

    def get_is_overdue(self, obj):
        return obj.is_overdue

    def create(self, validated_data):
        validated_data['nase_znacka'] = generate_nase_znacka()
        return super().create(validated_data)


class ReklamaceNotifikaceSerializer(serializers.ModelSerializer):
    reklamace_id = serializers.IntegerField(read_only=True)
    nase_znacka = serializers.CharField(source='reklamace.nase_znacka', read_only=True)

    class Meta:
        model = ReklamaceNotifikace
        fields = ['id', 'reklamace_id', 'nase_znacka', 'message', 'typ', 'created_at', 'read_at']
        read_only_fields = fields


class ReklamacePotvrditSerializer(serializers.Serializer):
    zpusob_vyrizeni = serializers.ChoiceField(choices=ZpusobVyrizeni.choices)
    datum_vyrizeni = serializers.DateField(required=False, allow_null=True)
    sklad_vyskladneno = serializers.BooleanField(required=False, default=False)
    sklad_naskladneno = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        instance = self.context['instance']
        if instance.status != ReklamaceStatus.ODESLANE:
            raise serializers.ValidationError('Potvrdit lze jen odeslanou reklamaci.')
        return attrs
