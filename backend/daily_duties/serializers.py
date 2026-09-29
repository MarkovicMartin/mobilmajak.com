from rest_framework import serializers

from .models import DailyDutyTemplate
from .periods import ACTIVE_PERIODS, PERIOD_LABELS
from .permissions import user_label


class DailyDutyTemplateSerializer(serializers.ModelSerializer):
    periodicity_display = serializers.SerializerMethodField()
    prodejna_nazev = serializers.SerializerMethodField()
    uzivatel_jmeno = serializers.SerializerMethodField()

    class Meta:
        model = DailyDutyTemplate
        fields = [
            'id', 'title', 'description', 'periodicity', 'periodicity_display',
            'prodejna', 'prodejna_nazev', 'uzivatel', 'uzivatel_jmeno',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_periodicity_display(self, obj):
        return PERIOD_LABELS.get(obj.periodicity, obj.periodicity)

    def get_prodejna_nazev(self, obj):
        return obj.prodejna.nazev if obj.prodejna_id else ''

    def get_uzivatel_jmeno(self, obj):
        return user_label(obj.uzivatel)

    def validate(self, attrs):
        periodicity = attrs.get('periodicity', getattr(self.instance, 'periodicity', None))
        if periodicity not in ACTIVE_PERIODS:
            raise serializers.ValidationError({
                'periodicity': 'Povolené hodnoty jsou daily, weekly a monthly.',
            })
        if 'prodejna' in attrs:
            prodejna = attrs.get('prodejna')
        else:
            prodejna = getattr(self.instance, 'prodejna', None) if self.instance else None
        if 'uzivatel' in attrs:
            uzivatel = attrs.get('uzivatel')
        else:
            uzivatel = getattr(self.instance, 'uzivatel', None) if self.instance else None
        if bool(prodejna) == bool(uzivatel):
            raise serializers.ValidationError(
                'Vyplňte právě prodejnu, nebo právě jednoho uživatele.'
            )
        return attrs
