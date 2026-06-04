from django.utils import timezone
from rest_framework import serializers

from stores.models import Prodejna
from users.models import WebUser

from .models import Ukol, UkolKomentar
from .urgency import urgency_for_task


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
    is_unread = serializers.SerializerMethodField()

    class Meta:
        model = Ukol
        fields = [
            "id",
            "ukol",
            "priorita",
            "deadline",
            "deadline_cas",
            "stav",
            "typ",
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
            "is_unread",
        ]
        read_only_fields = ["vytvoreno", "upraveno", "dokonceno_v", "precteno_v"]

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

    def get_prodejna(self, obj):
        if not obj.id_prodejny:
            return None
        self._ensure_maps(obj)
        return self._store_map.get(obj.id_prodejny)

    def get_urgency(self, obj):
        return urgency_for_task(obj)

    def get_is_unread(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return False
        from .urgency import is_task_unread

        return is_task_unread(obj, request.user)

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

    def update(self, instance, validated_data):
        new_stav = validated_data.get("stav", instance.stav)
        if new_stav == "hotovo" and instance.stav != "hotovo":
            validated_data["dokonceno_v"] = timezone.now()
        elif new_stav != "hotovo" and "stav" in validated_data:
            validated_data["dokonceno_v"] = None
        return super().update(instance, validated_data)

    def create(self, validated_data):
        if validated_data.get("stav") == "hotovo":
            validated_data["dokonceno_v"] = timezone.now()
        return super().create(validated_data)


def serialize_tasks_list(tasks, request):
    tasks_list = list(tasks)
    serializer = UkolSerializer(tasks_list, many=True, context={"request": request})
    if tasks_list:
        serializer.child._prefetch_maps(tasks_list)
    return serializer.data
