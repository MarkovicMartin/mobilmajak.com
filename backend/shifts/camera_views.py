"""
Webhook pro pilot pohybu (bez obrazu).
"""
import json

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from stores.models import Prodejna

from .camera_hikvision import parse_hikvision_alarm
from .camera_motion import (
    load_motion_secrets,
    record_motion_event,
    verify_motion_signature,
    verify_motion_token,
)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def camera_motion_event(request):
    """
    Brána na prodejně: { "prodejna_id": 12, "motion": true|false, "at": "ISO8601" (volitelné) }

    Hlavičky: X-Mobilmajak-Timestamp (unix s), X-Mobilmajak-Signature (HMAC-SHA256 hex).
    """
    if not load_motion_secrets():
        return Response(
            {'error': 'Pilot kamer není na serveru nakonfigurován (CAMERA_MOTION_SECRETS)'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return Response({'error': 'Neplatný JSON'}, status=status.HTTP_400_BAD_REQUEST)

    prodejna_id = data.get('prodejna_id')
    motion = data.get('motion')
    if prodejna_id is None or motion is None:
        return Response({'error': 'Chybí prodejna_id nebo motion'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        prodejna_id = int(prodejna_id)
    except (TypeError, ValueError):
        return Response({'error': 'Neplatné prodejna_id'}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(motion, bool):
        return Response({'error': 'motion musí být true nebo false'}, status=status.HTTP_400_BAD_REQUEST)

    ok, err = verify_motion_signature(request, prodejna_id)
    if not ok:
        return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

    if not Prodejna.objects.filter(pk=prodejna_id, aktivni=True).exists():
        return Response({'error': 'Neznámá prodejna'}, status=status.HTTP_404_NOT_FOUND)

    cas = timezone.now()
    at_raw = data.get('at')
    if at_raw:
        parsed = parse_datetime(str(at_raw))
        if parsed:
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
            cas = parsed

    event = record_motion_event(
        prodejna_id=prodejna_id,
        pohyb=motion,
        cas=cas,
        zdroj=str(data.get('source') or 'gateway')[:32],
    )

    return Response({
        'ok': True,
        'id': event.id,
        'prodejna_id': prodejna_id,
        'motion': motion,
        'recorded_at': event.cas.isoformat(),
    })


@csrf_exempt
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def camera_hikvision_webhook(request, prodejna_id, token):
    """
    Přímý HTTP alarm z NVR (bez brány na prodejně).
    URL: /api/shifts/camera-events/hikvision/<prodejna_id>/<token>/
    Token = stejný secret jako v CAMERA_MOTION_SECRETS.
    """
    if not load_motion_secrets():
        return Response(
            {'error': 'Pilot kamer není nakonfigurován'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    ok, err = verify_motion_token(prodejna_id, token)
    if not ok:
        return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

    if not Prodejna.objects.filter(pk=prodejna_id, aktivni=True).exists():
        return Response({'error': 'Neznámá prodejna'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({'ok': True, 'message': 'Hikvision webhook endpoint ready'})

    parsed = parse_hikvision_alarm(request.body or b'')
    if parsed.get('ignored') or parsed.get('motion') is None:
        return Response({
            'ok': True,
            'ignored': True,
            'reason': parsed.get('reason') or parsed.get('event_type'),
        })

    event = record_motion_event(
        prodejna_id=prodejna_id,
        pohyb=parsed['motion'],
        cas=parsed.get('cas'),
        zdroj='nvr-http',
    )

    return Response({
        'ok': True,
        'id': event.id,
        'prodejna_id': prodejna_id,
        'motion': parsed['motion'],
        'event_type': parsed.get('event_type'),
        'recorded_at': event.cas.isoformat(),
    })
