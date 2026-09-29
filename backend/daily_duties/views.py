from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DailyDutyCompletion, DailyDutyTemplate
from .periods import ACTIVE_PERIODS, PERIOD_LABELS, period_bounds, period_label
from .permissions import DailyDutiesModuleGate, IsAdminRole, user_label, user_matches_template
from .serializers import DailyDutyTemplateSerializer


def parse_day(raw):
    if not raw:
        return timezone.localdate()
    try:
        return datetime.strptime(str(raw), '%Y-%m-%d').date()
    except ValueError:
        return None


def templates_for_user(user):
    query = Q(uzivatel_id=user.id)
    if getattr(user, 'prodejna_id', None):
        query |= Q(prodejna_id=user.prodejna_id)
    return (
        DailyDutyTemplate.objects.filter(is_active=True, periodicity__in=ACTIVE_PERIODS)
        .filter(query)
        .select_related('prodejna', 'uzivatel')
        .order_by('title')
    )


def completion_map(templates, day):
    if not templates:
        return {}, {}
    bounds = {}
    for template in templates:
        start, end = period_bounds(template.periodicity, day)
        bounds[template.id] = (start, end)
    completions = DailyDutyCompletion.objects.filter(
        template_id__in=[template.id for template in templates],
        period_start__in={start for start, _end in bounds.values()},
    ).select_related('completed_by')
    found = {}
    for completion in completions:
        start = bounds.get(completion.template_id, (None, None))[0]
        if completion.period_start == start:
            found[completion.template_id] = completion
    return bounds, found


def completion_payload(completion):
    if not completion:
        return None
    return {
        'id': completion.id,
        'note': completion.note,
        'completed_at': completion.completed_at,
        'completed_by_id': completion.completed_by_id,
        'completed_by_name': user_label(completion.completed_by),
    }


def item_payload(template, day, bounds, completion, *, include_can_complete, user):
    start, end = bounds[template.id]
    completed = completion is not None
    target_type = 'uzivatel' if template.uzivatel_id else 'prodejna'
    if target_type == 'uzivatel':
        target_label = user_label(template.uzivatel)
    else:
        target_label = template.prodejna.nazev if template.prodejna_id else ''
    payload = {
        'id': template.id,
        'title': template.title,
        'description': template.description,
        'periodicity': template.periodicity,
        'periodicity_display': PERIOD_LABELS.get(template.periodicity, template.periodicity),
        'target_type': target_type,
        'target_label': target_label,
        'period_start': start.isoformat(),
        'period_end': end.isoformat(),
        'period_label': period_label(template.periodicity, start, end),
        'completed': completed,
        'completion': completion_payload(completion),
    }
    if include_can_complete:
        payload['can_complete'] = (not completed) and user_matches_template(user, template)
    return payload


class DailyDutyTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = DailyDutyTemplateSerializer
    permission_classes = [DailyDutiesModuleGate, IsAuthenticated, IsAdminRole]
    queryset = DailyDutyTemplate.objects.select_related('prodejna', 'uzivatel')
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']


class MyDutiesView(APIView):
    permission_classes = [DailyDutiesModuleGate, IsAuthenticated]

    def get(self, request):
        day = parse_day(request.query_params.get('date'))
        if day is None:
            return Response({'detail': 'Neplatné datum.'}, status=status.HTTP_400_BAD_REQUEST)
        templates = list(templates_for_user(request.user))
        bounds, found = completion_map(templates, day)
        items = [
            item_payload(
                template, day, bounds, found.get(template.id),
                include_can_complete=True, user=request.user,
            )
            for template in templates
        ]
        return Response({'date': day.isoformat(), 'items': items})


class CompleteDutyView(APIView):
    permission_classes = [DailyDutiesModuleGate, IsAuthenticated]

    def post(self, request, pk):
        day = parse_day(request.data.get('date'))
        if day is None:
            return Response({'detail': 'Neplatné datum.'}, status=status.HTTP_400_BAD_REQUEST)
        template = get_object_or_404(
            DailyDutyTemplate.objects.select_related('prodejna', 'uzivatel'),
            pk=pk,
            is_active=True,
            periodicity__in=ACTIVE_PERIODS,
        )
        if not user_matches_template(request.user, template):
            return Response(
                {'detail': 'Tuto položku nemůžete odškrtnout.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        start, end = period_bounds(template.periodicity, day)
        note = str(request.data.get('note') or '').strip()[:2000]
        try:
            with transaction.atomic():
                completion = DailyDutyCompletion.objects.create(
                    template=template,
                    period_start=start,
                    completed_by=request.user,
                    note=note,
                )
        except IntegrityError:
            return Response(
                {'detail': 'V tomto období je položka už splněná.'},
                status=status.HTTP_409_CONFLICT,
            )
        bounds = {template.id: (start, end)}
        item = item_payload(
            template, day, bounds, completion,
            include_can_complete=True, user=request.user,
        )
        return Response(item, status=status.HTTP_201_CREATED)


class DutyStatusView(APIView):
    permission_classes = [DailyDutiesModuleGate, IsAuthenticated, IsAdminRole]

    def get(self, request):
        day = parse_day(request.query_params.get('date'))
        if day is None:
            return Response({'detail': 'Neplatné datum.'}, status=status.HTTP_400_BAD_REQUEST)
        templates = list(
            DailyDutyTemplate.objects.filter(is_active=True, periodicity__in=ACTIVE_PERIODS)
            .select_related('prodejna', 'uzivatel')
            .order_by('title')
        )
        bounds, found = completion_map(templates, day)
        items = [
            item_payload(
                template, day, bounds, found.get(template.id),
                include_can_complete=False, user=request.user,
            )
            for template in templates
        ]
        return Response({'date': day.isoformat(), 'items': items})
