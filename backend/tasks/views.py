from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import WebUser

from .models import Ukol, UkolKomentar
from .permissions import (
    assignees_for_store,
    is_task_manager,
    tasks_queryset_for_user,
    user_can_access_task,
    user_can_edit_task,
    validate_task_create,
    vedouci_store_ids,
)
from .serializers import UkolKomentarSerializer, UkolSerializer, serialize_tasks_list
from .urgency import notifications_counts_for_user, urgency_for_task

OPEN_TASK_STATUSES = ('novy', 'v_procesu')


def _parse_month(mesic: str):
    rok, mesic_cislo = map(int, mesic.split("-"))
    return rok, mesic_cislo


def _filter_tasks_queryset(qs, request):
    stav = request.GET.get("stav", "vse")
    if stav and stav != "vse":
        qs = qs.filter(stav=stav)

    typ = request.GET.get("typ")
    if typ:
        qs = qs.filter(typ=typ)

    prodejce_id = request.GET.get("prodejce_id")
    if prodejce_id:
        qs = qs.filter(id_prodejce_ukol=prodejce_id)

    mesic = request.GET.get("mesic")
    if mesic:
        try:
            rok, mesic_cislo = _parse_month(mesic)
            qs = qs.filter(
                Q(deadline__year=rok, deadline__month=mesic_cislo)
                | Q(deadline__isnull=True, vytvoreno__year=rok, vytvoreno__month=mesic_cislo)
            )
        except (ValueError, TypeError):
            pass

    scope = request.GET.get("scope")
    if scope == "mine":
        qs = qs.filter(
            Q(id_prodejce_ukol=request.user.id)
            | (Q(typ="osobni") & Q(id_prodejce_zadal=request.user.id))
        )

    prodejna_id = request.GET.get("prodejna_id")
    if prodejna_id:
        qs = qs.filter(id_prodejny=prodejna_id)

    return qs


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def tasks_list_create(request):
    if request.method == "GET":
        qs = _filter_tasks_queryset(tasks_queryset_for_user(request.user), request)
        limit = min(int(request.GET.get("limit", 200)), 500)
        tasks = list(qs.order_by("-vytvoreno")[:limit])
        return Response(serialize_tasks_list(tasks, request))

    data = request.data.copy()
    role = getattr(request.user, "role", None)

    if not is_task_manager(request.user):
        data["typ"] = "osobni"
        data.setdefault("id_prodejce_ukol", request.user.id)
        data.setdefault("id_prodejce_zadal", request.user.id)
    else:
        data.setdefault("id_prodejce_zadal", request.user.id)
        if data.get("typ") == "prirazeny" and not data.get("id_prodejce_ukol"):
            return Response(
                {"error": "U přiřazeného úkolu je povinný přiřazený uživatel."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    err = validate_task_create(request.user, data)
    if err:
        return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

    if data.get("typ") != "prirazeny":
        if not is_task_manager(request.user):
            data["id_prodejce_ukol"] = request.user.id
            data["id_prodejce_zadal"] = request.user.id
            data["id_prodejny"] = None
        elif role == "VEDOUCI" and not data.get("id_prodejny"):
            store_ids = vedouci_store_ids(request.user)
            if len(store_ids) == 1:
                data["id_prodejny"] = store_ids[0]

    serializer = UkolSerializer(data=data, context={"request": request})
    if serializer.is_valid():
        task = serializer.save()
        if task.typ == "prirazeny" and task.id_prodejce_ukol != request.user.id:
            task.precteno_v = None
            task.save(update_fields=["precteno_v"])
        out = UkolSerializer(task, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def task_detail(request, task_id: int):
    try:
        task = Ukol.objects.get(id=task_id)
    except Ukol.DoesNotExist:
        return Response({"error": "Úkol nenalezen"}, status=status.HTTP_404_NOT_FOUND)

    if not user_can_access_task(request.user, task):
        return Response({"error": "Nemáte oprávnění"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        return Response(UkolSerializer(task, context={"request": request}).data)

    if not user_can_edit_task(request.user, task):
        return Response({"error": "Nemáte oprávnění k úpravě"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "DELETE":
        if not is_task_manager(request.user) and task.id_prodejce_zadal != request.user.id:
            return Response({"error": "Nemáte oprávnění ke smazání"}, status=status.HTTP_403_FORBIDDEN)
        task.delete()
        return Response({"message": "Úkol smazán"})

    serializer = UkolSerializer(task, data=request.data, partial=True, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tasks_calendar(request):
    mesic = request.GET.get("mesic")
    if not mesic:
        return Response({"error": "Chybí parametr mesic (YYYY-MM)."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        rok, mesic_cislo = _parse_month(mesic)
    except (ValueError, TypeError):
        return Response({"error": "Neplatný formát měsíce."}, status=status.HTTP_400_BAD_REQUEST)

    qs = tasks_queryset_for_user(request.user).filter(
        Q(deadline__year=rok, deadline__month=mesic_cislo)
        | Q(deadline__isnull=True, vytvoreno__year=rok, vytvoreno__month=mesic_cislo)
    )
    qs = _filter_tasks_queryset(qs, request)

    kalendar_data = {}
    for task in qs.order_by("deadline", "deadline_cas"):
        if task.deadline:
            datum_str = task.deadline.strftime("%Y-%m-%d")
        else:
            datum_str = task.vytvoreno.strftime("%Y-%m-%d")
        if datum_str not in kalendar_data:
            kalendar_data[datum_str] = []
        kalendar_data[datum_str].append(
            {
                "id": task.id,
                "ukol": task.ukol,
                "stav": task.stav,
                "priorita": task.priorita,
                "typ": task.typ,
                "urgency": urgency_for_task(task),
                "deadline_cas": task.deadline_cas.strftime("%H:%M") if task.deadline_cas else None,
            }
        )

    return Response({"kalendar_data": kalendar_data, "mesic": mesic})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def task_comments(request, task_id: int):
    try:
        task = Ukol.objects.get(id=task_id)
    except Ukol.DoesNotExist:
        return Response({"error": "Úkol nenalezen"}, status=status.HTTP_404_NOT_FOUND)

    if not user_can_access_task(request.user, task):
        return Response({"error": "Nemáte oprávnění"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        comments = task.komentare.all()
        return Response(UkolKomentarSerializer(comments, many=True).data)

    text = (request.data.get("text") or "").strip()
    if not text:
        return Response({"error": "Text komentáře je povinný."}, status=status.HTTP_400_BAD_REQUEST)

    jmeno = f"{getattr(request.user, 'jmeno', '')} {getattr(request.user, 'prijmeni', '')}".strip()
    comment = UkolKomentar.objects.create(
        ukol=task,
        autor_id=request.user.id,
        autor_jmeno=jmeno or str(request.user.id),
        text=text,
    )
    return Response(UkolKomentarSerializer(comment).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def task_mark_read(request, task_id: int):
    try:
        task = Ukol.objects.get(id=task_id)
    except Ukol.DoesNotExist:
        return Response({"error": "Úkol nenalezen"}, status=status.HTTP_404_NOT_FOUND)

    if task.id_prodejce_ukol != request.user.id:
        return Response({"error": "Označit přečtení může jen přiřazený uživatel."}, status=status.HTTP_403_FORBIDDEN)

    task.precteno_v = timezone.now()
    task.save(update_fields=["precteno_v", "upraveno"])
    return Response({"success": True, "precteno_v": task.precteno_v})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tasks_notifications_summary(request):
    counts = notifications_counts_for_user(request.user)
    return Response({"success": True, **counts})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tasks_unread_summary(request):
    """Zpětná kompatibilita – počítá nepřečtené přiřazené úkoly (precteno_v)."""
    counts = notifications_counts_for_user(request.user)
    return Response({"success": True, "unread_count": counts["tasks_unread"]})


def _serialize_dashboard_task(task, assignees_map):
    return {
        'id': task.id,
        'ukol': task.ukol,
        'stav': task.stav,
        'priorita': task.priorita,
        'deadline': task.deadline.isoformat() if task.deadline else None,
        'deadline_cas': task.deadline_cas.strftime('%H:%M') if task.deadline_cas else None,
        'urgency': urgency_for_task(task),
        'assignee': assignees_map.get(task.id_prodejce_ukol, ''),
        'prodejna_id': task.id_prodejny,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tasks_dashboard_snapshot(request):
    """Admin: úkoly s termínem dnes + náhled příštích 7 dní."""
    if getattr(request.user, 'role', None) != 'ADMIN':
        return Response({'error': 'Nemáte oprávnění'}, status=status.HTTP_403_FORBIDDEN)

    today = timezone.localdate()
    week_end = today + timedelta(days=7)
    qs = tasks_queryset_for_user(request.user).filter(stav__in=OPEN_TASK_STATUSES)

    today_qs = qs.filter(deadline=today).order_by('deadline_cas', 'priorita')
    week_qs = qs.filter(
        deadline__gt=today,
        deadline__lte=week_end,
    ).order_by('deadline', 'deadline_cas')[:25]

    all_tasks = list(today_qs) + list(week_qs)
    user_ids = {t.id_prodejce_ukol for t in all_tasks}
    assignees_map = {
        u.id: f'{u.jmeno} {u.prijmeni}'.strip()
        for u in WebUser.objects.filter(id__in=user_ids)
    }

    return Response({
        'datum': today.isoformat(),
        'today': [_serialize_dashboard_task(t, assignees_map) for t in today_qs],
        'week_preview': [_serialize_dashboard_task(t, assignees_map) for t in week_qs],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tasks_assignees(request):
    if not is_task_manager(request.user):
        return Response({"error": "Nemáte oprávnění"}, status=status.HTTP_403_FORBIDDEN)

    prodejna_id = request.GET.get("prodejna_id")
    if not prodejna_id:
        return Response({"error": "Chybí parametr prodejna_id."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        store_id = int(prodejna_id)
    except (TypeError, ValueError):
        return Response({"error": "Neplatné prodejna_id."}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"assignees": assignees_for_store(store_id, request.user)})
