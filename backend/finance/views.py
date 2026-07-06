"""Finance API – všechny endpointy ADMIN-only."""
from datetime import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .fio_status import FIO_DISABLED_MESSAGE, get_fio_import_status
from .models import FinanceDoklad, FioKategorizacniPravidlo, NakladKategorie, NakladPolozka
from .permissions import (
    accessible_store_ids,
    finance_admin_view,
    finance_invoice_view,
    is_finance_admin,
    naklady_qs_for_invoice_user,
    user_can_upload_doklad,
)
from .doklady import link_doklad_to_polozka, serialize_doklad
from .faktura_process import process_doklad_ocr, schvalit_doklad, zamitnout_doklad
from .services import (
    get_finance_counts,
    get_last_fio_import_info,
    log_finance_audit,
    resolve_dph_stav,
    serialize_naklad_polozka,
    serialize_naklad_polozky,
    serialize_pravidlo,
    typ_platby_from_castka,
)


def _no_store_response(data, status_code=status.HTTP_200_OK):
    resp = Response(data, status=status_code)
    resp['Cache-Control'] = 'no-store'
    return resp


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def finance_status(request):
    fio = get_fio_import_status()
    counts = get_finance_counts()
    last_import = get_last_fio_import_info()
    log_finance_audit(request, 'status')
    return _no_store_response({
        'fio': {
            'available': fio['available'],
            'enabled': fio['enabled'],
            'message': fio['message'] or FIO_DISABLED_MESSAGE,
            'last_import': last_import,
        },
        'counts': counts,
        'manual_naklady': True,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def naklad_kategorie_list(request):
    log_finance_audit(request, 'kategorie_list')
    rows = NakladKategorie.objects.filter(aktivni=True).order_by('poradi', 'nazev')
    return _no_store_response([
        {
            'id': k.id,
            'nazev': k.nazev,
            'poradi': k.poradi,
            'parent_id': k.parent_id,
            'typ_dph': k.typ_dph,
        }
        for k in rows
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def naklady_nezarazene(request):
    log_finance_audit(request, 'naklady_nezarazene')
    bez_faktury = request.GET.get('bez_faktury', '').strip().lower() in ('1', 'true', 'yes')
    if bez_faktury:
        qs = (
            NakladPolozka.objects.filter(
                dph_stav=NakladPolozka.DPH_STAV_CEKA,
                typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
                ignorovat=False,
                doklad__isnull=True,
            )
            .exclude(stav=NakladPolozka.STAV_IGNOROVAT)
            .select_related('kategorie', 'doklad')
            .order_by('-datum', '-id')
        )
    else:
        qs = (
            NakladPolozka.objects.filter(stav=NakladPolozka.STAV_NEZARAZENO)
            .select_related('kategorie', 'doklad')
            .order_by('-datum', '-id')
        )
    return _no_store_response(serialize_naklad_polozky(qs[:500]))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def naklady_prehled(request):
    """Přehled zařazení – auto / ručně / chybí."""
    log_finance_audit(request, 'naklady_prehled')
    stav = (request.GET.get('stav') or 'vse').strip().lower()
    zdroj = (request.GET.get('zdroj') or '').strip()
    qs = (
        NakladPolozka.objects.filter(typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI)
        .select_related('kategorie', 'doklad')
        .order_by('-datum', '-id')
    )
    if stav == 'nezarazeno':
        qs = qs.filter(stav=NakladPolozka.STAV_NEZARAZENO)
    elif stav == 'auto':
        qs = qs.filter(stav=NakladPolozka.STAV_ZARAZENO, zarazeno_automaticky=True)
    elif stav == 'rucne':
        qs = qs.filter(stav=NakladPolozka.STAV_RUCNE)
    elif stav == 'ignorovat':
        qs = qs.filter(stav=NakladPolozka.STAV_IGNOROVAT)
  # vse = all outgoing
    if zdroj in (NakladPolozka.ZDROJ_FIO, NakladPolozka.ZDROJ_SYMPLIO_POKLADNA):
        qs = qs.filter(zdroj=zdroj)
    return _no_store_response(serialize_naklad_polozky(qs[:400]))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def naklad_manual_create(request):
    data = request.data
    try:
        datum = datetime.strptime(data.get('datum', ''), '%Y-%m-%d').date()
        castka = data.get('castka')
        if castka is None or castka == '':
            return _no_store_response({'error': 'Chybí castka'}, status.HTTP_400_BAD_REQUEST)
    except ValueError:
        return _no_store_response({'error': 'Neplatný datum (YYYY-MM-DD)'}, status.HTTP_400_BAD_REQUEST)

    kategorie_id = data.get('kategorie_id') or None
    if kategorie_id:
        try:
            kategorie_id = int(kategorie_id)
        except (TypeError, ValueError):
            return _no_store_response({'error': 'Neplatná kategorie'}, status.HTTP_400_BAD_REQUEST)

    prodejna_id = data.get('prodejna_id')
    if prodejna_id not in (None, ''):
        try:
            prodejna_id = int(prodejna_id)
        except (TypeError, ValueError):
            return _no_store_response({'error': 'Neplatná prodejna'}, status.HTTP_400_BAD_REQUEST)
    else:
        prodejna_id = None

    typ_platby = typ_platby_from_castka(castka)
    dph_stav = resolve_dph_stav(kategorie_id, typ_platby)

    polozka = NakladPolozka.objects.create(
        datum=datum,
        rok=datum.year,
        mesic=datum.month,
        castka=castka,
        kategorie_id=kategorie_id,
        prodejna_id=prodejna_id,
        stav=NakladPolozka.STAV_ZARAZENO if kategorie_id else NakladPolozka.STAV_NEZARAZENO,
        zdroj=NakladPolozka.ZDROJ_MANUAL,
        popis=(data.get('popis') or '')[:500],
        poznamka_admin=(data.get('poznamka_admin') or '')[:2000],
        typ_platby=typ_platby,
        dph_stav=dph_stav,
        upravil_user_id=request.user.id,
        upraveno=timezone.now(),
    )
    log_finance_audit(request, 'naklad_manual_create', f'id={polozka.id}')
    return _no_store_response(serialize_naklad_polozka(polozka), status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def naklad_update(request, polozka_id):
    try:
        polozka = NakladPolozka.objects.get(pk=polozka_id)
    except NakladPolozka.DoesNotExist:
        return _no_store_response({'error': 'Položka nenalezena'}, status.HTTP_404_NOT_FOUND)

    data = request.data
    if 'kategorie_id' in data:
        kid = data.get('kategorie_id')
        polozka.kategorie_id = int(kid) if kid not in (None, '') else None
    if 'prodejna_id' in data:
        pid = data.get('prodejna_id')
        polozka.prodejna_id = int(pid) if pid not in (None, '') else None
    if 'stav' in data:
        polozka.stav = data['stav']
    if 'ignorovat' in data:
        polozka.ignorovat = bool(data['ignorovat'])
        if polozka.ignorovat:
            polozka.stav = NakladPolozka.STAV_IGNOROVAT
    if 'poznamka_admin' in data:
        polozka.poznamka_admin = (data.get('poznamka_admin') or '')[:2000]
    if 'dph_stav' in data:
        new_dph = data['dph_stav']
        if new_dph in dict(NakladPolozka.DPH_STAV_CHOICES):
            if new_dph == NakladPolozka.DPH_STAV_BEZ and polozka.kategorie_id:
                kat = NakladKategorie.objects.filter(pk=polozka.kategorie_id).first()
                if kat and kat.typ_dph != NakladKategorie.TYP_DPH_BEZ:
                    return _no_store_response(
                        {'error': 'bez_dph lze nastavit jen u kategorií bez DPH (mzdy, odvody…)'},
                        status.HTTP_400_BAD_REQUEST,
                    )
            polozka.dph_stav = new_dph

    if data.get('zaradit'):
        if not polozka.kategorie_id:
            return _no_store_response({'error': 'Pro zařazení vyberte kategorii'}, status.HTTP_400_BAD_REQUEST)
        polozka.stav = NakladPolozka.STAV_RUCNE
        polozka.ignorovat = False
        polozka.dph_stav = resolve_dph_stav(polozka.kategorie_id, polozka.typ_platby)

    polozka.upravil_user_id = request.user.id
    polozka.upraveno = timezone.now()
    polozka.save()
    log_finance_audit(request, 'naklad_update', f'id={polozka.id}')
    return _no_store_response(serialize_naklad_polozka(polozka))


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def pravidla_list_create(request):
    if request.method == 'GET':
        log_finance_audit(request, 'pravidla_list')
        qs = FioKategorizacniPravidlo.objects.select_related('kategorie').order_by('-id')
        return _no_store_response([serialize_pravidlo(r) for r in qs[:200]])

    data = request.data
    rule = FioKategorizacniPravidlo.objects.create(
        protiucet=(data.get('protiucet') or '')[:64],
        zprava_obsahuje=(data.get('zprava_obsahuje') or '')[:200],
        vs=(data.get('vs') or '')[:32],
        kategorie_id=data.get('kategorie_id') or None,
        prodejna_id=data.get('prodejna_id') or None,
        ignorovat=bool(data.get('ignorovat')),
        vytvoril_user_id=request.user.id,
    )
    log_finance_audit(request, 'pravidlo_create', f'id={rule.id}')
    return _no_store_response(serialize_pravidlo(rule), status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def pravidlo_delete(request, pravidlo_id):
    try:
        rule = FioKategorizacniPravidlo.objects.get(pk=pravidlo_id)
    except FioKategorizacniPravidlo.DoesNotExist:
        return _no_store_response({'error': 'Pravidlo nenalezeno'}, status.HTTP_404_NOT_FOUND)
    rule.delete()
    log_finance_audit(request, 'pravidlo_delete', f'id={pravidlo_id}')
    return _no_store_response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_invoice_view
def naklady_ceka_na_fakturu(request):
    """Výdaje čekající na přiložení faktury – prodejce vidí svou prodejnu."""
    log_finance_audit(request, 'naklady_ceka_na_fakturu')
    qs = (
        NakladPolozka.objects.filter(
            dph_stav=NakladPolozka.DPH_STAV_CEKA,
            typ_platby=NakladPolozka.TYP_PLATBY_ODCHOZI,
            ignorovat=False,
            doklad__isnull=True,
        )
        .exclude(stav=NakladPolozka.STAV_IGNOROVAT)
        .select_related('kategorie', 'doklad')
        .order_by('-datum', '-id')
    )
    store_ids = accessible_store_ids(request.user)
    if store_ids is not None:
        qs = qs.filter(prodejna_id__in=store_ids)
    qs = naklady_qs_for_invoice_user(qs, request.user)
    return _no_store_response(serialize_naklad_polozky(qs[:300]))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@finance_invoice_view
def doklad_upload(request):
    """Nahrání faktury (PDF/foto) k existující položce nákladu."""
    upload = request.FILES.get('file')
    if not upload:
        return _no_store_response({'error': 'Chybí soubor (file)'}, status.HTTP_400_BAD_REQUEST)

    try:
        polozka_id = int(request.data.get('naklad_polozka_id', ''))
    except (TypeError, ValueError):
        return _no_store_response({'error': 'Chybí naklad_polozka_id'}, status.HTTP_400_BAD_REQUEST)

    try:
        polozka = NakladPolozka.objects.get(pk=polozka_id)
    except NakladPolozka.DoesNotExist:
        return _no_store_response({'error': 'Položka nenalezena'}, status.HTTP_404_NOT_FOUND)

    if not user_can_upload_doklad(request.user, polozka):
        return _no_store_response({'error': 'Nemáte oprávnění k této položce'}, status.HTTP_403_FORBIDDEN)

    try:
        doklad = link_doklad_to_polozka(
            polozka,
            upload,
            dodavatel_nazev=request.data.get('dodavatel_nazev', ''),
            cislo_faktury=request.data.get('cislo_faktury', ''),
            castka_bez_dph=request.data.get('castka_bez_dph'),
            dph_castka=request.data.get('dph_castka'),
            dph_sazba=request.data.get('dph_sazba'),
            user_id=request.user.id,
        )
    except ValueError as exc:
        return _no_store_response({'error': str(exc)}, status.HTTP_400_BAD_REQUEST)

    log_finance_audit(request, 'doklad_upload', f'polozka={polozka.id} doklad={doklad.id}')
    polozka.refresh_from_db()
    return _no_store_response({
        'doklad': serialize_doklad(doklad, include_polozka=True),
        'polozka': serialize_naklad_polozka(polozka),
    }, status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def doklady_ke_kontrole(request):
    """Fronta faktur ke kontrole před Flexi."""
    log_finance_audit(request, 'doklady_ke_kontrole')
    qs = FinanceDoklad.objects.filter(
        stav__in=(
            FinanceDoklad.STAV_CEKA_NA_OCR,
            FinanceDoklad.STAV_KE_KONTROLE,
            FinanceDoklad.STAV_NOVA,
        ),
    ).select_related('naklad_polozka').order_by('-vytvoreno')
    return _no_store_response([
        serialize_doklad(d, include_polozka=True) for d in qs[:100]
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def doklad_schvalit(request, doklad_id: int):
    try:
        doklad = FinanceDoklad.objects.select_related('naklad_polozka').get(pk=doklad_id)
    except FinanceDoklad.DoesNotExist:
        return _no_store_response({'error': 'Doklad nenalezen'}, status.HTTP_404_NOT_FOUND)
    doklad = schvalit_doklad(doklad, request.user.id)
    log_finance_audit(request, 'doklad_schvalit', f'id={doklad_id}')
    return _no_store_response(serialize_doklad(doklad, include_polozka=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def doklad_zamitnout(request, doklad_id: int):
    try:
        doklad = FinanceDoklad.objects.get(pk=doklad_id)
    except FinanceDoklad.DoesNotExist:
        return _no_store_response({'error': 'Doklad nenalezen'}, status.HTTP_404_NOT_FOUND)
    duvod = (request.data.get('duvod') or '')[:500]
    doklad = zamitnout_doklad(doklad, request.user.id, duvod=duvod)
    log_finance_audit(request, 'doklad_zamitnout', f'id={doklad_id}')
    return _no_store_response(serialize_doklad(doklad, include_polozka=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def doklad_reprocess_ocr(request, doklad_id: int):
    try:
        doklad = process_doklad_ocr(doklad_id, overwrite_empty=False)
    except FinanceDoklad.DoesNotExist:
        return _no_store_response({'error': 'Doklad nenalezen'}, status.HTTP_404_NOT_FOUND)
    log_finance_audit(request, 'doklad_reprocess_ocr', f'id={doklad_id}')
    return _no_store_response(serialize_doklad(doklad, include_polozka=True))


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@finance_admin_view
def doklad_update(request, doklad_id: int):
    try:
        doklad = FinanceDoklad.objects.select_related('naklad_polozka').get(pk=doklad_id)
    except FinanceDoklad.DoesNotExist:
        return _no_store_response({'error': 'Doklad nenalezen'}, status.HTTP_404_NOT_FOUND)

    data = request.data
    text_fields = ('dodavatel_nazev', 'cislo_faktury', 'dodavatel_ico')
    for field in text_fields:
        if field in data:
            setattr(doklad, field, str(data[field] or '')[:200])

    from decimal import Decimal, InvalidOperation
    for field in ('castka_bez_dph', 'dph_castka', 'castka_celkem'):
        if field in data:
            raw = data[field]
            if raw in (None, ''):
                setattr(doklad, field, None)
            else:
                try:
                    setattr(doklad, field, Decimal(str(raw).replace(',', '.')))
                except InvalidOperation:
                    return _no_store_response({'error': f'Neplatná částka: {field}'}, status.HTTP_400_BAD_REQUEST)

    if 'dph_sazba' in data and data['dph_sazba'] not in (None, ''):
        try:
            doklad.dph_sazba = int(data['dph_sazba'])
        except (TypeError, ValueError):
            return _no_store_response({'error': 'Neplatná sazba DPH'}, status.HTTP_400_BAD_REQUEST)

    from .faktura_match import match_doklad_to_polozka
    match = match_doklad_to_polozka(doklad, doklad.naklad_polozka)
    doklad.match_stav = match['stav']
    doklad.match_detail = match
    doklad.stav = FinanceDoklad.STAV_KE_KONTROLE
    doklad.upraveno = timezone.now()
    doklad.save()

    log_finance_audit(request, 'doklad_update', f'id={doklad_id}')
    return _no_store_response(serialize_doklad(doklad, include_polozka=True))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@finance_invoice_view
def doklady_list(request):
    """Nahráté faktury bez DPH (čekají na doplnění / OCR)."""
    log_finance_audit(request, 'doklady_list')
    qs = FinanceDoklad.objects.filter(
        stav__in=(
            FinanceDoklad.STAV_CEKA_NA_OCR,
            FinanceDoklad.STAV_KE_KONTROLE,
            FinanceDoklad.STAV_NOVA,
        ),
    ).select_related('naklad_polozka')
    store_ids = accessible_store_ids(request.user)
    if store_ids is not None:
        qs = qs.filter(naklad_polozka__prodejna_id__in=store_ids)
    if not is_finance_admin(request.user):
        qs = qs.filter(naklad_polozka__zdroj=NakladPolozka.ZDROJ_SYMPLIO_POKLADNA)
    return _no_store_response([serialize_doklad(d) for d in qs.order_by('-vytvoreno')[:50]])
