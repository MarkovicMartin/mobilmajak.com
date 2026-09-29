"""API modulu Kategorie zboží."""
from datetime import date

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .kategorie_zbozi import (
    BODY_ZA_KATEGORII,
    ClaimObsazeny,
    NeniVAuditu,
    UzPotvrzeno,
    moje_body,
    obohatit_o_claimy,
    polozky_kodu,
    produkty_mesice,
    zaloz_claim,
    zrus_claim,
)


def _rok_mesic(request):
    today = date.today()
    try:
        rok = int(request.GET.get('rok') or request.data.get('rok') or today.year)
        mesic = int(request.GET.get('mesic') or request.data.get('mesic') or today.month)
    except (TypeError, ValueError):
        return None
    if not (1 <= mesic <= 12) or rok < 2000 or rok > 2100:
        return None
    return rok, mesic


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kategorie_zbozi_seznam(request):
    parsed = _rok_mesic(request)
    if not parsed:
        return Response({'error': 'Neplatný měsíc.'}, status=status.HTTP_400_BAD_REQUEST)
    rok, mesic = parsed
    radky = obohatit_o_claimy(produkty_mesice(rok, mesic), request.user)
    return Response({
        'rok': rok,
        'mesic': mesic,
        'body_za_kategorii': BODY_ZA_KATEGORII,
        'moje_body': moje_body(request.user, rok, mesic),
        'radky': radky,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kategorie_zbozi_polozky(request):
    parsed = _rok_mesic(request)
    kod = (request.GET.get('kod') or '').strip()
    if not parsed or not kod:
        return Response({'error': 'Chybí měsíc nebo kód.'}, status=status.HTTP_400_BAD_REQUEST)
    rok, mesic = parsed
    return Response({
        'rok': rok,
        'mesic': mesic,
        'kod': kod,
        'polozky': polozky_kodu(rok, mesic, kod),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kategorie_zbozi_claim(request):
    parsed = _rok_mesic(request)
    kod = (request.data.get('kod') or '').strip()
    if not parsed or not kod:
        return Response({'error': 'Chybí měsíc nebo kód.'}, status=status.HTTP_400_BAD_REQUEST)
    rok, mesic = parsed
    try:
        claim = zaloz_claim(request.user, kod, rok, mesic)
    except ClaimObsazeny:
        return Response({'error': 'Tenhle kód už někdo odškrtl.'}, status=status.HTTP_409_CONFLICT)
    except UzPotvrzeno:
        return Response({'error': 'Za tenhle kód už byly připsány body.'}, status=status.HTTP_409_CONFLICT)
    except NeniVAuditu:
        return Response({'error': 'Kód v auditu toho měsíce není.'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'id': claim.id, 'kod': claim.kod, 'stav': claim.stav})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def kategorie_zbozi_claim_zrusit(request, claim_id):
    if not zrus_claim(request.user, claim_id):
        return Response({'error': 'Odškrtnutí nelze zrušit.'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'ok': True})
