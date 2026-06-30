"""API endpointy pro modul Zásilkovna konverze."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from analytics.permissions import require_analytics_login
from analytics.zasilkovna_konverze import build_konverze_report


def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    return datetime.strptime(value, '%Y-%m-%d').date()


@require_http_methods(['GET'])
@require_analytics_login
def zasilkovna_konverze_view(request):
    try:
        today = date.today()
        default_from = today.replace(day=1)
        default_to = today - timedelta(days=1)
        if default_to < default_from:
            default_to = today

        date_from = _parse_date(request.GET.get('date_from'), default_from)
        date_to = _parse_date(request.GET.get('date_to'), default_to)
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        prodejna_id = request.GET.get('prodejna_id')
        pid = int(prodejna_id) if prodejna_id else None
        if pid is not None and pid not in range(1, 7):
            return JsonResponse({'success': False, 'error': 'prodejna_id musí být 1–6'}, status=400)

        report = build_konverze_report(date_from, date_to, prodejna_id=pid)
        return JsonResponse({'success': True, **report})
    except ValueError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)
