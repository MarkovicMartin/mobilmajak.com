from django.utils import timezone
from rest_framework import serializers

from stores.models import Prodejna
from users.models import WebUser

from .models import Ukol, UkolKomentar
from .urgency import is_at_risk, urgency_for_task


def _user_name_map(user_ids: set[int]) -> dict[int, dict]:
    if not user_ids:
        return {}
    users = WebUser.objects.filter(id__in=user_ids)
    return {
        u.id: {
            "id": u.id,
            "jmeno": u.jmeno,
            "prijmeni": u.prijmeni,
            "jmeno_plne": f"{u.jmeno} {u.prijmeni}".strip(),
        }
        for u in users
    }


def _store_name_map(store_ids: set[int]) -> dict[int, dict]:
    if not store_ids:
        return {}
    stores = Prodejna.objects.filter(id__in=store_ids)
    return {
        s.id: {
            "id": s.id,
            "nazev": (s.nazev_kratkiy or s.nazev or "").strip(),
        }
        for s in stores
    }


class UkolKomentarSerializer(serializers.ModelSerializer):
    class Meta:
        model = UkolKomentar
        fields = ["id", "autor_id", "autor_jmeno", "text", "vytvoreno"]


class UkolSerializer(serializers.ModelSerializer):
    assignee = serializers.SerializerMethodField()
    zadavatel = serializers.SerializerMethodField()
    prodejna = serializers.SerializerMethodField()
    urgency = serializers.SerializerMethodField()
    at_risk = serializers.SerializerMethodField()
    is_unread = serializers.SerializerMethodField()
    komentare_count = serializers.SerializerMethodField()
    schvalil = serializers.SerializerMethodField()
    potvrdit_mid_kontrolu = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Ukol
        fields = [
            "id",
            "ukol",
            "vysledek",
            "popis",
            "dod_polozky",
            "priorita",
            "termin_zadani",
            "deadline",
            "deadline_cas",
            "stav",
            "typ",
            "blokovano_duvod",
            "vyzaduje_schvaleni",
            "schvaleno_v",
            "schvalil_id",
            "schvalil",
            "start_potvrzeno_v",
            "prvni_krok",
            "mid_kontrola_v",
            "posledni_aktivita_v",
            "precteno_v",
            "id_prodejce_ukol",
            "id_prodejce_zadal",
            "id_prodejny",
            "vytvoreno",
            "upraveno",
            "dokonceno_v",
            "assignee",
            "zadavatel",
            "prodejna",
            "urgency",
            "at_risk",
            "is_unread",
            "komentare_count",
            "potvrdit_mid_kontrolu",
        ]
        read_only_fields = [
            "vytvoreno",
            "upraveno",
            "dokonceno_v",
            "precteno_v",
            "schvaleno_v",
            "schvalil_id",
            "start_potvrzeno_v",
            "posledni_aktivita_v",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_map = None
        self._store_map = None

    def _prefetch_maps(self, tasks):
        user_ids = set()
        store_ids = set()
        for t in tasks:
            user_ids.add(t.id_prodejce_ukol)
            user_ids.add(t.id_prodejce_zadal)
            if t.schvalil_id:
                user_ids.add(t.schvalil_id)
            if t.id_prodejny:
                store_ids.add(t.id_prodejny)
        self._user_map = _user_name_map(user_ids)
        self._store_map = _store_name_map(store_ids)

    def _ensure_maps(self, obj):
        if self._user_map is None:
            self._prefetch_maps([obj])

    def get_assignee(self, obj):
        self._ensure_maps(obj)
        return self._user_map.get(obj.id_prodejce_ukol)

    def get_zadavatel(self, obj):
        self._ensure_maps(obj)
        return self._user_map.get(obj.id_prodejce_zadal)

    def get_schvalil(self, obj):
        if not obj.schvalil_id:
            return None
        self._ensure_maps(obj)
        return self._user_map.get(obj.schvalil_id)

    def get_prodejna(self, obj):
        if not obj.id_prodejny:
            return None
        self._ensure_maps(obj)
        return self._store_map.get(obj.id_prodejny)

    def get_urgency(self, obj):
        return urgency_for_task(obj)

    def get_at_risk(self, obj):
        return is_at_risk(obj)

    def get_is_unread(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return False
        from .urgency import is_task_unread

        return is_task_unread(obj, request.user)

    def get_komentare_count(self, obj):
        if hasattr(obj, 'komentare_count'):
            return obj.komentare_count
        return obj.komentare.count()

    def validate_priorita(self, value):
        if value not in dict(Ukol.PRIORITY):
            raise serializers.ValidationError("Neplatná priorita.")
        return value

    def validate_stav(self, value):
        if value not in dict(Ukol.STAVY):
            raise serializers.ValidationError("Neplatný stav.")
        return value

    def validate_typ(self, value):
        if value not in dict(Ukol.TYPY):
            raise serializers.ValidationError("Neplatný typ.")
        return value

    def _touch_activity(self, validated_data, instance=None):
        validated_data["posledni_aktivita_v"] = timezone.now()

    def _apply_state_side_effects(self, instance, validated_data, user=None):
        new_stav = validated_data.get("stav", instance.stav)
        now = timezone.now()

        if new_stav == "v_procesu" and instance.stav == "novy" and instance.typ == "prirazeny":
            validated_data.setdefault("start_potvrzeno_v", now)

        if new_stav == "ceka_schvaleni":
            validated_data["dokonceno_v"] = None

        if new_stav == "hotovo" and instance.stav != "hotovo":
            validated_data["dokonceno_v"] = now
            if instance.vyzaduje_schvaleni and instance.stav == "ceka_schvaleni" and user:
                validated_data["schvaleno_v"] = now
                validated_data["schvalil_id"] = user.id
        elif new_stav != "hotovo" and "stav" in validated_data:
            if new_stav != "ceka_schvaleni":
                validated_data["dokonceno_v"] = None

        if validated_data.get("mid_kontrola_v") is True:
            validated_data["mid_kontrola_v"] = now

    def update(self, instance, validated_data):
        potvrdit_mid = validated_data.pop("potvrdit_mid_kontrolu", False)
        if potvrdit_mid:
            validated_data["mid_kontrola_v"] = timezone.now()

        request = self.context.get("request")
        user = request.user if request else None

        activity_fields = {
            "stav", "dod_polozky", "blokovano_duvod", "prvni_krok",
            "popis", "vysledek", "ukol", "priorita", "termin_zadani", "deadline", "mid_kontrola_v",
        }
        if activity_fields & set(validated_data.keys()):
            self._touch_activity(validated_data, instance)

        self._apply_state_side_effects(instance, validated_data, user=user)
        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data.pop("potvrdit_mid_kontrolu", None)
        validated_data["posledni_aktivita_v"] = timezone.now()
        if validated_data.get("stav") == "hotovo":
            validated_data["dokonceno_v"] = timezone.now()
        return super().create(validated_data)


def serialize_tasks_list(tasks, request):
    tasks_list = list(tasks)
    serializer = UkolSerializer(tasks_list, many=True, context={"request": request})
    if tasks_list:
        serializer.child._prefetch_maps(tasks_list)
    return serializer.data
