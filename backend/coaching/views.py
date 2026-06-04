from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from coaching.aggregate import (
    _parse_month,
    build_roster,
    build_seller_profile,
    build_seller_tasks,
    build_seller_workload,
    build_timeline,
    compare_sellers,
)
from coaching.models import CoachingGoal, CoachingNote
from coaching.permissions import (
    CoachingAccessPermission,
    allowed_store_ids,
    filter_prodejna_id_param,
    user_can_access_seller,
)
from coaching.serializers import CoachingGoalSerializer, CoachingNoteSerializer
from stores.models import Prodejna
from users.exclusions import real_sales_staff_queryset
from users.models import WebUser


def _month_params(request):
    ym = request.GET.get('mesic')
    rok = request.GET.get('rok')
    mesic = request.GET.get('mesic_cislo')
    if ym and '-' in ym:
        rok_i, mesic_i = _parse_month(ym)
    elif rok and mesic:
        rok_i, mesic_i = int(rok), int(mesic)
    else:
        rok_i, mesic_i = _parse_month(None)
    return rok_i, mesic_i


@api_view(['GET'])
@permission_classes([CoachingAccessPermission])
def filters_options(request):
    stores = allowed_store_ids(request.user)
    qs = Prodejna.objects.filter(aktivni=True).order_by('nazev')
    if stores is not None:
        qs = qs.filter(id__in=stores)
    staff_qs = real_sales_staff_queryset()
    if stores is not None:
        staff_qs = staff_qs.filter(prodejna_id__in=stores)
    return Response({
        'success': True,
        'prodejny': [{'id': p.id, 'nazev': p.nazev} for p in qs],
        'prodejci': [
            {
                'id': u.id,
                'jmeno': u.jmeno,
                'prijmeni': u.prijmeni,
                'prodejna_id': u.prodejna_id,
            }
            for u in staff_qs
        ],
    })


@api_view(['GET'])
@permission_classes([CoachingAccessPermission])
def roster_view(request):
    rok, mesic = _month_params(request)
    prodejna_id = filter_prodejna_id_param(request.user, request.GET.get('prodejna_id'))
    kanal = request.GET.get('kanal', 'all')
    store_ids = allowed_store_ids(request.user)
    if prodejna_id == -1:
        return Response({'success': True, 'prodejci': [], 'rok': rok, 'mesic': mesic})
    data = build_roster(
        rok, mesic,
        prodejna_id=prodejna_id,
        kanal=kanal,
        store_ids=store_ids,
    )
    return Response({'success': True, 'prodejci': data, 'rok': rok, 'mesic': mesic})


@api_view(['GET'])
@permission_classes([CoachingAccessPermission])
def seller_profile(request, user_id):
    try:
        seller = WebUser.objects.get(pk=user_id)
    except WebUser.DoesNotExist:
        return Response({'success': False, 'error': 'Prodejce nenalezen'}, status=404)
    if not user_can_access_seller(request.user, seller):
        return Response({'success': False, 'error': 'Nemáte oprávnění'}, status=403)
    rok, mesic = _month_params(request)
    kanal = request.GET.get('kanal', 'all')
    profile = build_seller_profile(user_id, rok, mesic, kanal=kanal)
    notes = CoachingNote.objects.filter(prodejce_id=user_id).order_by('-vytvoreno')[:50]
    goals = CoachingGoal.objects.filter(prodejce_id=user_id).order_by('-vytvoreno')[:50]
    return Response({
        'success': True,
        'profile': profile,
        'notes': CoachingNoteSerializer(notes, many=True).data,
        'goals': CoachingGoalSerializer(goals, many=True).data,
    })


@api_view(['GET'])
@permission_classes([CoachingAccessPermission])
def seller_timeline(request, user_id):
    try:
        seller = WebUser.objects.get(pk=user_id)
    except WebUser.DoesNotExist:
        return Response({'success': False, 'error': 'Prodejce nenalezen'}, status=404)
    if not user_can_access_seller(request.user, seller):
        return Response({'success': False, 'error': 'Nemáte oprávnění'}, status=403)
    rok, mesic = _month_params(request)
    raw_metrics = request.GET.get('metrics', 'polozky_nad_100')
    metrics = [m.strip() for m in raw_metrics.split(',') if m.strip()]
    compare = request.GET.get('compare')
    data = build_timeline(
        user_id, metrics, rok, mesic,
        compare=compare,
        kanal=request.GET.get('kanal', 'all'),
    )
    return Response({'success': True, **data})


@api_view(['GET'])
@permission_classes([CoachingAccessPermission])
def seller_tasks(request, user_id):
    try:
        seller = WebUser.objects.get(pk=user_id)
    except WebUser.DoesNotExist:
        return Response({'success': False, 'error': 'Prodejce nenalezen'}, status=404)
    if not user_can_access_seller(request.user, seller):
        return Response({'success': False, 'error': 'Nemáte oprávnění'}, status=403)
    rok, mesic = _month_params(request)
    kanal = request.GET.get('kanal', 'all')
    tasks = build_seller_tasks(user_id, rok, mesic)
    workload = build_seller_workload(user_id, rok, mesic, kanal=kanal)
    return Response({'success': True, 'tasks': tasks, **workload})


@api_view(['GET'])
@permission_classes([CoachingAccessPermission])
def sellers_compare(request):
    user_a = request.GET.get('user_a')
    user_b = request.GET.get('user_b')
    if not user_a or not user_b:
        return Response({'success': False, 'error': 'Chybí user_a nebo user_b'}, status=400)
    for uid in (user_a, user_b):
        try:
            seller = WebUser.objects.get(pk=int(uid))
        except (WebUser.DoesNotExist, ValueError):
            return Response({'success': False, 'error': 'Prodejce nenalezen'}, status=404)
        if not user_can_access_seller(request.user, seller):
            return Response({'success': False, 'error': 'Nemáte oprávnění'}, status=403)
    rok, mesic = _month_params(request)
    data = compare_sellers(int(user_a), int(user_b), rok, mesic, kanal=request.GET.get('kanal', 'all'))
    return Response({'success': True, **data})


@api_view(['GET', 'POST'])
@permission_classes([CoachingAccessPermission])
def notes_list_create(request):
    if request.method == 'GET':
        prodejce_id = request.GET.get('prodejce_id')
        qs = CoachingNote.objects.all().order_by('-vytvoreno')
        if prodejce_id:
            qs = qs.filter(prodejce_id=prodejce_id)
        stores = allowed_store_ids(request.user)
        if stores is not None:
            qs = qs.filter(prodejna_id__in=stores)
        return Response({'success': True, 'notes': CoachingNoteSerializer(qs[:100], many=True).data})

    prodejce_id = request.data.get('prodejce_id')
    if not prodejce_id:
        return Response({'success': False, 'error': 'Chybí prodejce_id'}, status=400)
    try:
        seller = WebUser.objects.get(pk=prodejce_id)
    except WebUser.DoesNotExist:
        return Response({'success': False, 'error': 'Prodejce nenalezen'}, status=404)
    if not user_can_access_seller(request.user, seller):
        return Response({'success': False, 'error': 'Nemáte oprávnění'}, status=403)
    ser = CoachingNoteSerializer(data=request.data)
    if ser.is_valid():
        note = ser.save(
            autor=request.user,
            prodejce_id=prodejce_id,
            prodejna_id=seller.prodejna_id,
        )
        return Response({'success': True, 'note': CoachingNoteSerializer(note).data}, status=201)
    return Response({'success': False, 'errors': ser.errors}, status=400)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([CoachingAccessPermission])
def note_detail(request, note_id):
    try:
        note = CoachingNote.objects.get(pk=note_id)
    except CoachingNote.DoesNotExist:
        return Response({'success': False, 'error': 'Poznámka nenalezena'}, status=404)
    if not user_can_access_seller(request.user, note.prodejce):
        return Response({'success': False, 'error': 'Nemáte oprávnění'}, status=403)
    if request.method == 'GET':
        return Response({'success': True, 'note': CoachingNoteSerializer(note).data})
    if request.method == 'DELETE':
        note.delete()
        return Response({'success': True})
    ser = CoachingNoteSerializer(note, data=request.data, partial=True)
    if ser.is_valid():
        ser.save()
        return Response({'success': True, 'note': ser.data})
    return Response({'success': False, 'errors': ser.errors}, status=400)


@api_view(['GET', 'POST'])
@permission_classes([CoachingAccessPermission])
def goals_list_create(request):
    if request.method == 'GET':
        prodejce_id = request.GET.get('prodejce_id')
        qs = CoachingGoal.objects.all().order_by('-vytvoreno')
        if prodejce_id:
            qs = qs.filter(prodejce_id=prodejce_id)
        stores = allowed_store_ids(request.user)
        if stores is not None:
            qs = qs.filter(prodejna_id__in=stores)
        return Response({'success': True, 'goals': CoachingGoalSerializer(qs[:100], many=True).data})

    prodejce_id = request.data.get('prodejce_id')
    if not prodejce_id:
        return Response({'success': False, 'error': 'Chybí prodejce_id'}, status=400)
    try:
        seller = WebUser.objects.get(pk=prodejce_id)
    except WebUser.DoesNotExist:
        return Response({'success': False, 'error': 'Prodejce nenalezen'}, status=404)
    if not user_can_access_seller(request.user, seller):
        return Response({'success': False, 'error': 'Nemáte oprávnění'}, status=403)
    ser = CoachingGoalSerializer(data=request.data)
    if ser.is_valid():
        goal = ser.save(
            autor=request.user,
            prodejce_id=prodejce_id,
            prodejna_id=seller.prodejna_id,
        )
        return Response({'success': True, 'goal': CoachingGoalSerializer(goal).data}, status=201)
    return Response({'success': False, 'errors': ser.errors}, status=400)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([CoachingAccessPermission])
def goal_detail(request, goal_id):
    try:
        goal = CoachingGoal.objects.get(pk=goal_id)
    except CoachingGoal.DoesNotExist:
        return Response({'success': False, 'error': 'Cíl nenalezen'}, status=404)
    if not user_can_access_seller(request.user, goal.prodejce):
        return Response({'success': False, 'error': 'Nemáte oprávnění'}, status=403)
    if request.method == 'GET':
        return Response({'success': True, 'goal': CoachingGoalSerializer(goal).data})
    if request.method == 'DELETE':
        goal.delete()
        return Response({'success': True})
    ser = CoachingGoalSerializer(goal, data=request.data, partial=True)
    if ser.is_valid():
        goal = ser.save()
        if goal.stav == 'splneny' and not goal.dokonceno_v:
            goal.dokonceno_v = timezone.now()
            goal.save(update_fields=['dokonceno_v'])
        return Response({'success': True, 'goal': CoachingGoalSerializer(goal).data})
    return Response({'success': False, 'errors': ser.errors}, status=400)
