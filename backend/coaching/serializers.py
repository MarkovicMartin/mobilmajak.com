from rest_framework import serializers

from coaching.models import CoachingGoal, CoachingNote


class CoachingNoteSerializer(serializers.ModelSerializer):
    autor_jmeno = serializers.SerializerMethodField()

    class Meta:
        model = CoachingNote
        fields = [
            'id', 'prodejce_id', 'autor_id', 'autor_jmeno', 'prodejna_id',
            'typ', 'text', 'vytvoreno', 'upraveno',
        ]
        read_only_fields = ['id', 'vytvoreno', 'upraveno', 'autor_id', 'autor_jmeno']

    def get_autor_jmeno(self, obj):
        if obj.autor:
            return f"{obj.autor.jmeno} {obj.autor.prijmeni}".strip()
        return ''


class CoachingGoalSerializer(serializers.ModelSerializer):
    autor_jmeno = serializers.SerializerMethodField()

    class Meta:
        model = CoachingGoal
        fields = [
            'id', 'prodejce_id', 'autor_id', 'autor_jmeno', 'prodejna_id',
            'nazev', 'popis', 'kategorie_metrika', 'cil_hodnota', 'jednotka',
            'termin', 'stav', 'vytvoreno', 'dokonceno_v',
        ]
        read_only_fields = ['id', 'vytvoreno', 'dokonceno_v', 'autor_id', 'autor_jmeno']

    def get_autor_jmeno(self, obj):
        if obj.autor:
            return f"{obj.autor.jmeno} {obj.autor.prijmeni}".strip()
        return ''
