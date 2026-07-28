"""Packeta API – import provizí pro Zásilkovna analytiku (ADMIN-only)."""
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .packeta_fetch import fetch_and_import_all_branches, import_packeta_rows
from .packeta_parser import parse_packeta_csv
from .permissions import packeta_admin_view
from .secrets import get_packeta_admin_credentials


def _no_store_response(data, status_code=status.HTTP_200_OK):
    resp = Response(data, status=status_code)
    resp['Cache-Control'] = 'no-store'
    return resp


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@packeta_admin_view
def packeta_status(request):
    admin = get_packeta_admin_credentials()
    return _no_store_response({
        'fetch_available': admin is not None,
        'admin_configured': admin is not None,
        'admin_label': admin['label'] if admin else None,
        'csv_upload': True,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@packeta_admin_view
def packeta_import_csv(request):
    upload = request.FILES.get('file')
    if not upload:
        return _no_store_response({'error': 'Chybí soubor (file)'}, status.HTTP_400_BAD_REQUEST)

    try:
        prodejna_id = int(request.data.get('prodejna_id', ''))
    except (TypeError, ValueError):
        return _no_store_response({'error': 'Chybí nebo neplatné prodejna_id'}, status.HTTP_400_BAD_REQUEST)

    if prodejna_id not in range(1, 7):
        return _no_store_response(
            {'error': 'prodejna_id musí být 1–6.'},
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        content = upload.read()
        rows = parse_packeta_csv(content)
    except ValueError as exc:
        return _no_store_response({'error': str(exc)}, status.HTTP_400_BAD_REQUEST)

    imp = import_packeta_rows(rows, prodejna_id)
    cache_info = None
    try:
        from analytics.zasilkovna_leaderboard_cache import refresh_after_packeta_import
        cache_info = refresh_after_packeta_import(source='packeta_csv_api')
    except Exception:
        cache_info = {'ok': False}
    return _no_store_response({
        'prodejna_id': prodejna_id,
        'import_batch': imp['import_batch'],
        'created': imp['created'],
        'skipped': imp['skipped'],
        'stats': imp['stats'],
        'warning': imp.get('warning'),
        'zasilkovna_leaderboard_cache': cache_info,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@packeta_admin_view
def packeta_fetch_all(request):
    if not get_packeta_admin_credentials():
        return _no_store_response(
            {'error': 'Packeta admin přihlašovací údaje nejsou nakonfigurovány.'},
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        days = int(request.data.get('days', 1))
    except (TypeError, ValueError):
        days = 1
    days = max(1, min(days, 31))

    try:
        result = fetch_and_import_all_branches(days=days, dry_run=False)
    except RuntimeError as exc:
        return _no_store_response({'error': str(exc)}, status.HTTP_502_BAD_GATEWAY)

    return _no_store_response(result)
