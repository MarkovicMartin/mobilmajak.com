from rest_framework import serializers

from users.models import WebUser

from .models import Prodejna
from .oteviraci_doba_utils import normalize_oteviraci_doba


class ProdejnaSerializer(serializers.ModelSerializer):
    """Serializer pro kompletní správu prodejen"""

    vedouci_jmeno = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Prodejna
        fields = [
            'id', 'nazev', 'nazev_kratkiy', 'nazev_google_sheets',
            'adresa', 'telefon', 'email',
            'otevreno_od', 'otevreno_do', 'oteviraci_doba',
            'vedouci_prodejny', 'vedouci_user_id', 'vedouci_jmeno',
            'aktivni', 'barva', 'poradi', 'poznamka',
            'datum_vytvoreni', 'datum_upravy',
        ]
        read_only_fields = ['datum_vytvoreni', 'datum_upravy', 'vedouci_jmeno']

    def get_vedouci_jmeno(self, obj):
        if not obj.vedouci_user_id:
            return None
        try:
            u = WebUser.objects.get(pk=obj.vedouci_user_id)
            return f'{u.jmeno} {u.prijmeni}'.strip()
        except WebUser.DoesNotExist:
            return None

    def validate_oteviraci_doba(self, value):
        return normalize_oteviraci_doba(value)

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else dict(data)

        time_fields = ['otevreno_od', 'otevreno_do']
        text_fields = ['adresa', 'telefon', 'email', 'vedouci_prodejny', 'poznamka', 'nazev_google_sheets']

        for field in time_fields + text_fields:
            if field in data and data[field] == '':
                data[field] = None

        if 'vedouci_user_id' in data and data['vedouci_user_id'] in ('', None):
            data['vedouci_user_id'] = None
        elif 'vedouci_user_id' in data:
            try:
                data['vedouci_user_id'] = int(data['vedouci_user_id'])
            except (TypeError, ValueError):
                data['vedouci_user_id'] = None

        if 'poradi' in data and isinstance(data['poradi'], str):
            try:
                data['poradi'] = int(data['poradi']) if data['poradi'] else 0
            except ValueError:
                data['poradi'] = 0

        return super().to_internal_value(data)

    def validate_nazev(self, value):
        instance = getattr(self, 'instance', None)
        if instance:
            if Prodejna.objects.exclude(pk=instance.pk).filter(nazev=value).exists():
                raise serializers.ValidationError("Prodejna s tímto názvem již existuje.")
        else:
            if Prodejna.objects.filter(nazev=value).exists():
                raise serializers.ValidationError("Prodejna s tímto názvem již existuje.")
        return value

    def validate_poradi(self, value):
        if value < 0:
            raise serializers.ValidationError("Pořadí musí být nezáporné číslo.")
        return value

    def validate_barva(self, value):
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Barva musí být ve formátu hex (např. #FF0000).")
        if value and len(value) != 7:
            raise serializers.ValidationError("Barva musí být 7 znaků dlouhá včetně # (např. #FF0000).")
        return value


class ProdejnaListSerializer(serializers.ModelSerializer):
    """Zjednodušený serializer pro seznam prodejen"""

    vedouci_jmeno = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Prodejna
        fields = [
            'id', 'nazev', 'nazev_kratkiy', 'aktivni',
            'barva', 'poradi', 'vedouci_prodejny', 'vedouci_user_id', 'vedouci_jmeno',
        ]

    def get_vedouci_jmeno(self, obj):
        if not obj.vedouci_user_id:
            return None
        try:
            u = WebUser.objects.get(pk=obj.vedouci_user_id)
            return f'{u.jmeno} {u.prijmeni}'.strip()
        except WebUser.DoesNotExist:
            return None


class ProdejnaChoiceSerializer(serializers.ModelSerializer):
    """Minimální serializer pro dropdown/choice seznamy"""

    class Meta:
        model = Prodejna
        fields = ['id', 'nazev', 'nazev_kratkiy']
