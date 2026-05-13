import math
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from stores.models import Prodejna
from users.models import WebUser
from .models import PlanMonth, PlanStore, PlanCategory, PlanProdejce, PlanProdejceKategorie, KATEGORIE_CHOICES
from .helpers import vypocti_prumerne_ceny
from .historie import vypocitej_plan_z_historie, historie_nahled, ChybejiciDataError
from .rozpocet import rozpoctij

MIN_CASTKA_FIRMA = Decimal('500000')
MAX_CASTKA_FIRMA = Decimal('90000000')
MAX_CASTKA_PRODEJNA = Decimal('2000000')
TOLERANCE_PROCENT = Decimal('0.5')

NAZVY_MESICU = {
    1: 'Leden', 2: 'Únor', 3: 'Březen', 4: 'Duben',
    5: 'Květen', 6: 'Červen', 7: 'Červenec', 8: 'Srpen',
    9: 'Září', 10: 'Říjen', 11: 'Listopad', 12: 'Prosinec'
}

KATEGORIE_NAZVY = dict(KATEGORIE_CHOICES)

VYCHOZI_KATEGORIE = [
    'NOVE_TELEFONY', 'BAZAROVE_TELEFONY',
    'PRISLUSENSTVI_SKLA', 'PRISLUSENSTVI_OBALY', 'PRISLUSENSTVI_OSTATNI',
    'SLUZBY', 'SERVIS', 'OSTATNI',
]


def serialize_plan(plan_mesic):
    prodejny = plan_mesic.prodejny.select_related('prodejna').prefetch_related('kategorie')
    return {
        'id': plan_mesic.id,
        'rok': plan_mesic.rok,
        'mesic': plan_mesic.mesic,
        'mesic_nazev': NAZVY_MESICU.get(plan_mesic.mesic, ''),
        'cislo_verze': plan_mesic.cislo_verze,
        'je_aktualni': plan_mesic.je_aktualni,
        'castka_celkem': str(plan_mesic.castka_celkem),
        'total_lock': plan_mesic.total_lock,
        'vytvoreno_kdy': plan_mesic.vytvoreno_kdy.isoformat(),
        'vytvoril': plan_mesic.vytvoril.jmeno if plan_mesic.vytvoril else None,
        'prodejny': [
            {
                'id': ps.id,
                'prodejna_id': ps.prodejna_id,
                'prodejna_nazev': ps.prodejna.nazev,
                'prodejna_nazev_kratky': ps.prodejna.nazev_kratkiy,
                'prodejna_barva': ps.prodejna.barva,
                'podil_procenta': str(ps.podil_procenta),
                'castka_prodejna': str(ps.castka_prodejna),
                'zamknuto': ps.zamknuto,
                'lock_mode': ps.lock_mode,
                'servis_lock_mode': ps.servis_lock_mode,
                'castka_prodej': str(ps.castka_prodej),
                'castka_servis': str(ps.castka_servis),
                'kategorie': [
                    {
                        'id': pk.id,
                        'kategorie_kod': pk.kategorie_kod,
                        'kategorie_nazev': KATEGORIE_NAZVY.get(pk.kategorie_kod, pk.kategorie_kod),
                        'podil_procenta': str(pk.podil_procenta),
                        'castka_kategorie': str(pk.castka_kategorie),
                        'lock_mode': pk.lock_mode,
                        'prumerna_cena_za_kus': str(pk.prumerna_cena_za_kus) if pk.prumerna_cena_za_kus else None,
                        'pocet_kusu': math.ceil(float(pk.castka_kategorie) / float(pk.prumerna_cena_za_kus))
                            if pk.prumerna_cena_za_kus and pk.prumerna_cena_za_kus > 0 else None,
                    }
                    for pk in ps.kategorie.all()
                ],
            }
            for ps in prodejny
        ],
    }


def _rovnomerne_rozlozeni(castka_celkem, prodejny_qs):
    """Vrátí list {prodejna, podil, castka} s rovnoměrným rozložením."""
    prodejny = list(prodejny_qs)
    n = len(prodejny)
    if n == 0:
        return []
    podil = (Decimal('100') / n).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    castka = (castka_celkem * podil / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    result = []
    for p in prodejny:
        result.append({'prodejna': p, 'podil': podil, 'castka': castka})
    # Dorovnání posledního záznamu kvůli zaokrouhlení
    if result:
        soucet = sum(r['castka'] for r in result)
        result[-1]['castka'] += castka_celkem - soucet
        soucet_podilu = sum(r['podil'] for r in result)
        result[-1]['podil'] += Decimal('100') - soucet_podilu
    return result


def _vychozi_kategorie(castka_prodejna):
    """Vrátí defaultní kategorie s rovnoměrným rozložením."""
    n = len(VYCHOZI_KATEGORIE)
    podil = (Decimal('100') / n).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    castka = (castka_prodejna * podil / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    result = []
    for kod in VYCHOZI_KATEGORIE:
        result.append({'kod': kod, 'podil': podil, 'castka': castka})
    if result:
        soucet = sum(r['castka'] for r in result)
        result[-1]['castka'] += castka_prodejna - soucet
        soucet_podilu = sum(r['podil'] for r in result)
        result[-1]['podil'] += Decimal('100') - soucet_podilu
    return result


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def plan_mesic(request, rok, mesic):
    """
    GET  – Vrátí aktuální plán + seznam verzí pro daný měsíc.
    POST – Vytvoří nový plán (rovnoměrný nebo kopie předchozího měsíce).
    """
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        verze = PlanMonth.objects.filter(rok=rok, mesic=mesic).order_by('-cislo_verze')
        aktualni = verze.filter(je_aktualni=True).first()

        return Response({
            'aktualni': serialize_plan(aktualni) if aktualni else None,
            'verze': [
                {
                    'id': v.id,
                    'cislo_verze': v.cislo_verze,
                    'je_aktualni': v.je_aktualni,
                    'castka_celkem': str(v.castka_celkem),
                    'vytvoreno_kdy': v.vytvoreno_kdy.isoformat(),
                }
                for v in verze
            ],
        })

    # POST – vytvoření nového plánu
    data = request.data
    copy_from_previous = data.get('copy_from_previous', False)
    create_from_history = data.get('create_from_history', False)
    castka_celkem_raw = data.get('castka_celkem')

    # create_from_history – plán z historie + růst (castka_celkem se ignoruje)
    if create_from_history:
        try:
            rust_procent = float(data.get('rust_procent', 10))
        except (TypeError, ValueError):
            rust_procent = 10
        try:
            castka_celkem, prodejny_data = vypocitej_plan_z_historie(rok, mesic, rust_procent)
        except ChybejiciDataError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        posledni = PlanMonth.objects.filter(rok=rok, mesic=mesic).order_by('-cislo_verze').first()
        nove_cislo_verze = (posledni.cislo_verze + 1) if posledni else 1
        prumerne_ceny = vypocti_prumerne_ceny(rok, mesic)
        with transaction.atomic():
            novy_plan = PlanMonth.objects.create(
                rok=rok, mesic=mesic, cislo_verze=nove_cislo_verze,
                je_aktualni=True, castka_celkem=castka_celkem,
                vytvoril=request.user
            )
            for item in prodejny_data:
                prodej = (item['castka_prodejna'] * Decimal('0.7')).quantize(Decimal('0.01'))
                servis = item['castka_prodejna'] - prodej
                ps = PlanStore.objects.create(
                    plan_mesic=novy_plan,
                    prodejna=item['prodejna'],
                    podil_procenta=item['podil_procenta'],
                    castka_prodejna=item['castka_prodejna'],
                    castka_prodej=prodej,
                    castka_servis=servis,
                )
                for kat in item['kategorie']:
                    PlanCategory.objects.create(
                        plan_prodejna=ps,
                        kategorie_kod=kat['kod'],
                        podil_procenta=kat['podil_procenta'],
                        castka_kategorie=kat['castka_kategorie'],
                        prumerna_cena_za_kus=prumerne_ceny.get(kat['kod']),
                    )
        return Response(serialize_plan(novy_plan), status=status.HTTP_201_CREATED)

    if not castka_celkem_raw:
        return Response({'error': 'Chybí castka_celkem.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        castka_celkem = Decimal(str(castka_celkem_raw))
    except Exception:
        return Response({'error': 'Neplatná castka_celkem.'}, status=status.HTTP_400_BAD_REQUEST)

    if castka_celkem < MIN_CASTKA_FIRMA or castka_celkem > MAX_CASTKA_FIRMA:
        return Response({
            'error': f'Celková částka musí být mezi {MIN_CASTKA_FIRMA:,.0f} a {MAX_CASTKA_FIRMA:,.0f} Kč.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Číslo nové verze
    posledni = PlanMonth.objects.filter(rok=rok, mesic=mesic).order_by('-cislo_verze').first()
    nove_cislo_verze = (posledni.cislo_verze + 1) if posledni else 1

    with transaction.atomic():
        novy_plan = PlanMonth.objects.create(
            rok=rok, mesic=mesic, cislo_verze=nove_cislo_verze,
            je_aktualni=True, castka_celkem=castka_celkem,
            vytvoril=request.user
        )

        if copy_from_previous:
            # Zkopíruj strukturu z předchozího měsíce
            prev_mesic = mesic - 1
            prev_rok = rok
            if prev_mesic == 0:
                prev_mesic = 12
                prev_rok -= 1
            prev_plan = PlanMonth.objects.filter(rok=prev_rok, mesic=prev_mesic, je_aktualni=True).first()
            if prev_plan:
                _kopiruj_strukturu(novy_plan, prev_plan, castka_celkem)
                return Response(serialize_plan(novy_plan), status=status.HTTP_201_CREATED)

        # Rovnoměrné rozložení
        prodejny = Prodejna.get_aktivni_prodejny()
        rozlozeni = _rovnomerne_rozlozeni(castka_celkem, prodejny)
        prumerne_ceny = vypocti_prumerne_ceny(rok, mesic)
        for item in rozlozeni:
            prodej = (item['castka'] * Decimal('0.7')).quantize(Decimal('0.01'))
            servis = item['castka'] - prodej
            ps = PlanStore.objects.create(
                plan_mesic=novy_plan,
                prodejna=item['prodejna'],
                podil_procenta=item['podil'],
                castka_prodejna=item['castka'],
                castka_prodej=prodej,
                castka_servis=servis,
            )
            for kat in _vychozi_kategorie(item['castka']):
                PlanCategory.objects.create(
                    plan_prodejna=ps,
                    kategorie_kod=kat['kod'],
                    podil_procenta=kat['podil'],
                    castka_kategorie=kat['castka'],
                    prumerna_cena_za_kus=prumerne_ceny.get(kat['kod']),
                )

    return Response(serialize_plan(novy_plan), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_historie_nahled(request, rok, mesic):
    """
    GET – Náhled plánu z historie (obrat minulý rok, návrh s růstem, prodejny, kategorie).
    Query: rust_procent (default 10).
    """
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        rust_procent = float(request.query_params.get('rust_procent', 10))
    except (TypeError, ValueError):
        rust_procent = 10

    nahled = historie_nahled(rok, mesic, rust_procent)
    return Response(nahled)


def _kopiruj_strukturu(novy_plan, zdrojovy_plan, nova_castka_celkem):
    """Zkopíruje strukturu prodejen a kategorií, přepočítá částky dle nové celkové.
    Průměrné ceny přepočítá znovu z aktuálních historických dat (ne kopíruje)."""
    stara_castka = zdrojovy_plan.castka_celkem
    koef = nova_castka_celkem / stara_castka if stara_castka else Decimal('1')
    prumerne_ceny = vypocti_prumerne_ceny(novy_plan.rok, novy_plan.mesic)

    for ps_src in zdrojovy_plan.prodejny.select_related('prodejna').prefetch_related('kategorie'):
        nova_castka_p = (ps_src.castka_prodejna * koef).quantize(Decimal('0.01'))
        ps_new = PlanStore.objects.create(
            plan_mesic=novy_plan,
            prodejna=ps_src.prodejna,
            podil_procenta=ps_src.podil_procenta,
            castka_prodejna=nova_castka_p,
            zamknuto=False,
            castka_prodej=(ps_src.castka_prodej * koef).quantize(Decimal('0.01')),
            castka_servis=(ps_src.castka_servis * koef).quantize(Decimal('0.01')),
        )
        for pk_src in ps_src.kategorie.all():
            PlanCategory.objects.create(
                plan_prodejna=ps_new,
                kategorie_kod=pk_src.kategorie_kod,
                podil_procenta=pk_src.podil_procenta,
                castka_kategorie=(pk_src.castka_kategorie * koef).quantize(Decimal('0.01')),
                prumerna_cena_za_kus=prumerne_ceny.get(pk_src.kategorie_kod),
            )


def _obohat_prodejny_nazvy(prodejny_data):
    """Pro warnings z rozpoctij doplní k prodejnám jejich jména (podle prodejna_id)."""
    ids = [p.get('prodejna_id') for p in prodejny_data if p.get('prodejna_id')]
    nazvy = {p.id: p.nazev for p in Prodejna.objects.filter(id__in=ids)}
    result = []
    for p in prodejny_data:
        p2 = dict(p)
        if not p2.get('prodejna_nazev'):
            p2['prodejna_nazev'] = nazvy.get(p2.get('prodejna_id'), f"Prodejna {p2.get('prodejna_id')}")
        result.append(p2)
    return result


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def plan_prepocet(request, rok, mesic):
    """POST – dry-run rozpočtu. Nezapisuje do DB.

    Tělo: { castka_celkem, total_lock, prodejny: [...] } (stejné schéma jako plan_ulozit).
    Vrací rozpoctij() výstup (včetně warnings).
    """
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    data = request.data or {}
    castka_celkem_input = data.get('castka_celkem', 0)
    total_lock = bool(data.get('total_lock', False))
    prodejny_data = _obohat_prodejny_nazvy(data.get('prodejny', []))

    vysledek = rozpoctij(castka_celkem_input, prodejny_data, total_lock=total_lock)

    # Stringify Decimal pro JSON kompatibilitu s FE (stejný styl jako serialize_plan)
    def _s(v):
        return str(v) if v is not None else None

    return Response({
        'castka_celkem': _s(vysledek['castka_celkem']),
        'castka_celkem_input': _s(vysledek['castka_celkem_input']),
        'total_lock': vysledek['total_lock'],
        'soucet_podilu': _s(vysledek['soucet_podilu']),
        'soucet_castek': _s(vysledek['soucet_castek']),
        'soucet_zamk_pct': _s(vysledek['soucet_zamk_pct']),
        'soucet_zamk_kc': _s(vysledek['soucet_zamk_kc']),
        'soucet_auto_pct': _s(vysledek['soucet_auto_pct']),
        'warnings': vysledek['warnings'],
        'prodejny': [
            {
                'prodejna_id': p['prodejna_id'],
                'prodejna_nazev': p.get('prodejna_nazev'),
                'podil_procenta': _s(p['podil_procenta']),
                'castka_prodejna': _s(p['castka_prodejna']),
                'castka_prodej': _s(p['castka_prodej']),
                'castka_servis': _s(p['castka_servis']),
                'lock_mode': p['lock_mode'],
                'servis_lock_mode': p['servis_lock_mode'],
                'kategorie': [
                    {
                        'kategorie_kod': k['kategorie_kod'],
                        'podil_procenta': _s(k['podil_procenta']),
                        'castka_kategorie': _s(k['castka_kategorie']),
                        'lock_mode': k['lock_mode'],
                        'prumerna_cena_za_kus': _s(k['prumerna_cena_za_kus']) if k.get('prumerna_cena_za_kus') is not None else None,
                    }
                    for k in p['kategorie']
                ],
            }
            for p in vysledek['prodejny']
        ],
    })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def plan_ulozit(request, rok, mesic):
    """
    PUT – Uloží změny plánu (nová verze nebo update aktuální).
    Tělo: { castka_celkem, total_lock, nova_verze, prodejny: [{prodejna_id, podil_procenta,
            castka_prodejna, lock_mode, servis_lock_mode, zamknuto (legacy),
            castka_prodej, castka_servis,
            kategorie: [{kategorie_kod, podil_procenta, castka_kategorie, lock_mode}]}] }

    Součet podílů ≠ 100 % ani překročení MAX_CASTKA_PRODEJNA už není hard-fail –
    vrací warnings[] a uloží finální hodnoty spočtené přes rozpoctij().
    """
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    try:
        castka_celkem_input = Decimal(str(data['castka_celkem']))
    except (KeyError, Exception):
        return Response({'error': 'Chybí nebo je neplatná castka_celkem.'}, status=status.HTTP_400_BAD_REQUEST)

    if castka_celkem_input < MIN_CASTKA_FIRMA or castka_celkem_input > MAX_CASTKA_FIRMA:
        return Response({
            'error': f'Celková částka musí být mezi {MIN_CASTKA_FIRMA:,.0f} a {MAX_CASTKA_FIRMA:,.0f} Kč.'
        }, status=status.HTTP_400_BAD_REQUEST)

    total_lock = bool(data.get('total_lock', False))
    prodejny_data = _obohat_prodejny_nazvy(data.get('prodejny', []))

    # 1) Přepočet přes společnou funkci – zajistí respektování zámků
    vysledek = rozpoctij(castka_celkem_input, prodejny_data, total_lock=total_lock)
    warnings_list = list(vysledek['warnings'])

    # 2) MAX_CASTKA_PRODEJNA – už jen warning
    for p_final in vysledek['prodejny']:
        if p_final['castka_prodejna'] > MAX_CASTKA_PRODEJNA:
            prodejna_nazev = p_final.get('prodejna_nazev') or f"Prodejna {p_final.get('prodejna_id')}"
            warnings_list.append(
                f"{prodejna_nazev}: částka {p_final['castka_prodejna']:,.0f} Kč "
                f"překračuje doporučené maximum {MAX_CASTKA_PRODEJNA:,.0f} Kč."
            )

    castka_celkem_final = vysledek['castka_celkem']
    # Držíme se MIN/MAX hard-validace i pro dorovnaný celek
    if castka_celkem_final < MIN_CASTKA_FIRMA:
        castka_celkem_final = MIN_CASTKA_FIRMA
    if castka_celkem_final > MAX_CASTKA_FIRMA:
        warnings_list.append(
            f"Dorovnaná celková částka {castka_celkem_final:,.0f} Kč překračuje limit – "
            f"uloženo {MAX_CASTKA_FIRMA:,.0f} Kč."
        )
        castka_celkem_final = MAX_CASTKA_FIRMA

    nova_verze = data.get('nova_verze', False)
    prumerne_ceny = vypocti_prumerne_ceny(rok, mesic)

    # Mapování finálních hodnot per prodejna_id pro snadný přístup
    finalni_per_id = {p['prodejna_id']: p for p in vysledek['prodejny']}
    # Mapování originálního payloadu per prodejna_id (pro lock_mode, zamknuto a kategorie)
    input_per_id = {p.get('prodejna_id'): p for p in prodejny_data}

    with transaction.atomic():
        aktualni = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()

        if not aktualni or nova_verze:
            plany_prodejcu_po_prodejne = {}
            if aktualni:
                for ps in aktualni.prodejny.prefetch_related('plany_prodejcu__kategorie').all():
                    prodejci_data = []
                    for pp in ps.plany_prodejcu.all():
                        kat_dict = {
                            k.kategorie_kod: {'pocet_kusu': k.pocet_kusu, 'castka': k.castka}
                            for k in pp.kategorie.all()
                        }
                        prodejci_data.append((pp.uzivatel_id, kat_dict))
                    if prodejci_data:
                        plany_prodejcu_po_prodejne[ps.prodejna_id] = prodejci_data
            posledni = PlanMonth.objects.filter(rok=rok, mesic=mesic).order_by('-cislo_verze').first()
            cislo_verze = (posledni.cislo_verze + 1) if posledni else 1
            plan = PlanMonth.objects.create(
                rok=rok, mesic=mesic, cislo_verze=cislo_verze,
                je_aktualni=True, castka_celkem=castka_celkem_final,
                total_lock=total_lock,
                vytvoril=request.user,
            )
        else:
            plan = aktualni
            plan.castka_celkem = castka_celkem_final
            plan.total_lock = total_lock
            plan.save()
            plany_prodejcu_po_prodejne = {}
            for ps in plan.prodejny.prefetch_related('plany_prodejcu__kategorie').all():
                prodejci_data = []
                for pp in ps.plany_prodejcu.all():
                    kat_dict = {
                        k.kategorie_kod: {'pocet_kusu': k.pocet_kusu, 'castka': k.castka}
                        for k in pp.kategorie.all()
                    }
                    prodejci_data.append((pp.uzivatel_id, kat_dict))
                if prodejci_data:
                    plany_prodejcu_po_prodejne[ps.prodejna_id] = prodejci_data
            plan.prodejny.all().delete()

        for p_in in prodejny_data:
            pid = p_in.get('prodejna_id')
            p_final = finalni_per_id.get(pid)
            if not p_final:
                continue

            castka_p = Decimal(str(p_final['castka_prodejna']))
            podil = Decimal(str(p_final['podil_procenta']))
            castka_prodej = Decimal(str(p_final['castka_prodej']))
            castka_servis = Decimal(str(p_final['castka_servis']))

            lock_mode = p_final.get('lock_mode') or 'none'
            servis_lock_mode = p_final.get('servis_lock_mode') or 'none'
            # Legacy zamknuto: True pokud lock_mode = 'pct'; respektujeme i explicitní hodnotu z FE.
            zamknuto_legacy = bool(p_in.get('zamknuto', lock_mode == 'pct'))

            ps = PlanStore.objects.create(
                plan_mesic=plan,
                prodejna_id=pid,
                podil_procenta=podil,
                castka_prodejna=castka_p,
                zamknuto=zamknuto_legacy,
                lock_mode=lock_mode,
                servis_lock_mode=servis_lock_mode,
                castka_prodej=castka_prodej,
                castka_servis=castka_servis,
            )

            # Kategorie – bereme finální hodnoty z rozpočtu
            finalni_kat = {k['kategorie_kod']: k for k in p_final['kategorie']}
            input_kat = p_in.get('kategorie', []) or []

            if input_kat:
                for k_in in input_kat:
                    kod = k_in.get('kategorie_kod')
                    k_final = finalni_kat.get(kod)
                    if not k_final:
                        continue
                    k_podil = Decimal(str(k_final['podil_procenta']))
                    k_castka = Decimal(str(k_final['castka_kategorie']))
                    k_lock = k_final.get('lock_mode') or 'none'

                    prum_cena = None
                    if 'prumerna_cena_za_kus' in k_in and k_in['prumerna_cena_za_kus'] is not None:
                        try:
                            prum_cena = Decimal(str(k_in['prumerna_cena_za_kus']))
                        except Exception:
                            pass
                    if prum_cena is None:
                        prum_cena = prumerne_ceny.get(kod)

                    PlanCategory.objects.create(
                        plan_prodejna=ps,
                        kategorie_kod=kod,
                        podil_procenta=k_podil,
                        castka_kategorie=k_castka,
                        lock_mode=k_lock,
                        prumerna_cena_za_kus=prum_cena,
                    )
            else:
                for kat in _vychozi_kategorie(castka_p):
                    PlanCategory.objects.create(
                        plan_prodejna=ps,
                        kategorie_kod=kat['kod'],
                        podil_procenta=kat['podil'],
                        castka_kategorie=kat['castka'],
                        lock_mode='none',
                        prumerna_cena_za_kus=prumerne_ceny.get(kat['kod']),
                    )

            # Obnovení plánů prodejců z předchozí verze
            prodejci_data = plany_prodejcu_po_prodejne.get(pid, [])
            for uzivatel_id, kat_dict in prodejci_data:
                try:
                    uzivatel = WebUser.objects.get(id=uzivatel_id)
                except WebUser.DoesNotExist:
                    continue
                pp = PlanProdejce.objects.create(plan_prodejna=ps, uzivatel=uzivatel)
                for kod, hodnoty in kat_dict.items():
                    pocet = int(hodnoty.get('pocet_kusu', 0))
                    castka = Decimal(str(hodnoty.get('castka', 0)))
                    if pocet > 0 or castka > 0:
                        PlanProdejceKategorie.objects.create(
                            plan_prodejce=pp,
                            kategorie_kod=kod,
                            pocet_kusu=pocet,
                            castka=castka,
                        )

    response = serialize_plan(plan)
    response['warnings'] = warnings_list
    return Response(response)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def plan_set_aktualni(request, verze_id):
    """Nastaví vybranou verzi jako aktuální."""
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    from django.shortcuts import get_object_or_404
    verze = get_object_or_404(PlanMonth, id=verze_id)
    verze.je_aktualni = True
    verze.save()
    return Response({'message': f'Verze {verze.cislo_verze} nastavena jako aktuální.', 'id': verze.id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def muj_plan(request):
    """
    GET – Vrátí osobní plán přihlášeného prodejce pro daný měsíc.
    Query: rok, mesic (volitelné, výchozí = aktuální měsíc).
    Obsahuje plnění (skutečné kusy z WEB_PRODEJE_ALL) a trend.
    """
    from datetime import date
    import calendar
    from shifts.models import Smena
    from .plneni import plneni_prodejce, plneni_prodejce_do_data, plneni_prodejce_den

    today = date.today()
    rok = request.query_params.get('rok', today.year)
    mesic = request.query_params.get('mesic', today.month)
    try:
        rok = int(rok)
        mesic = int(mesic)
    except (ValueError, TypeError):
        rok = today.year
        mesic = today.month

    # Počet pracovních směn (typ_smeny='prace') pro přihlášeného uživatele v daném měsíci
    pracovnich_dni = Smena.objects.filter(
        user=request.user,
        datum__year=rok,
        datum__month=mesic,
        typ_smeny='prace',
        aktivni=True,
    ).count()

    # Počet směn pro dnešek (pro denní zobrazení) – pokud 0, frontend použije 19
    smen_dnes = 0
    plneni_dnes = {}
    if rok == today.year and mesic == today.month:
        smen_dnes = Smena.objects.filter(
            user=request.user,
            datum=today,
            typ_smeny='prace',
            aktivni=True,
        ).count()
        plneni_dnes = plneni_prodejce_den(today, request.user.id)

    plan_mesic = PlanMonth.objects.filter(
        rok=rok, mesic=mesic, je_aktualni=True
    ).first()

    if not plan_mesic:
        return Response({
            'rok': rok,
            'mesic': mesic,
            'mesic_nazev': NAZVY_MESICU.get(mesic, ''),
            'celkem_polozek': 0,
            'celkem_castka': '0.00',
            'kategorie': [],
            'pracovnich_dni': pracovnich_dni,
            'smen_dnes': smen_dnes,
            'plneni': None,
        })

    plany_pp = PlanProdejce.objects.filter(
        uzivatel=request.user,
        plan_prodejna__plan_mesic=plan_mesic,
    ).prefetch_related('kategorie')

    # Agregace kusů a částek přes všechny prodejny
    agregace = {}
    for pp in plany_pp:
        for k in pp.kategorie.all():
            kod = k.kategorie_kod
            if kod not in agregace:
                agregace[kod] = {'pocet_kusu': 0, 'castka': Decimal('0')}
            agregace[kod]['pocet_kusu'] += k.pocet_kusu
            agregace[kod]['castka'] += k.castka

    # Plnění z WEB_PRODEJE_ALL pro přihlášeného prodejce
    prodejce_id = request.user.id
    plneni_data = plneni_prodejce(rok, mesic, prodejce_id)
    trend_kategorie = {}
    je_aktualni_mesic = (rok == today.year and mesic == today.month)
    if je_aktualni_mesic:
        prvni_den = date(rok, mesic, 1)
        pocet_dni = (today - prvni_den).days + 1
        dni_v_mesici = calendar.monthrange(rok, mesic)[1]
        if pocet_dni >= 2:
            do_dnes = plneni_prodejce_do_data(rok, mesic, today, prodejce_id)
            for kod, kusy_d in do_dnes.items():
                prumer = kusy_d / pocet_dni if pocet_dni else 0
                trend_kategorie[kod] = {
                    'trend_kusy': round(prumer * dni_v_mesici),
                    'trend_procent': None,
                }

    kategorie = []
    celkem_skutecne = 0
    for kod, data in sorted(agregace.items()):
        plan_k = data['pocet_kusu']
        skut_k = plneni_data.get(kod, 0)
        skut_dnes = plneni_dnes.get(kod, 0)
        celkem_skutecne += skut_k
        pct = (skut_k / plan_k * 100) if plan_k > 0 else 0
        td = trend_kategorie.get(kod, {})
        trend_k = td.get('trend_kusy')
        trend_pct = (trend_k / plan_k * 100) if plan_k and trend_k is not None else None
        if trend_pct is not None:
            trend_pct = round(trend_pct, 1)
        kategorie.append({
            'kategorie_kod': kod,
            'kategorie_nazev': KATEGORIE_NAZVY.get(kod, kod),
            'pocet_kusu': data['pocet_kusu'],
            'castka': str(data['castka']),
            'skutecne_kusy': skut_k,
            'skutecne_dnes': skut_dnes,
            'plneni_procent': round(pct, 1),
            'trend_kusy': trend_k,
            'trend_procent': trend_pct,
        })

    celkem_polozek = sum(d['pocet_kusu'] for d in agregace.values())
    celkem_castka = sum(d['castka'] for d in agregace.values())
    plneni_celkem_pct = (celkem_skutecne / celkem_polozek * 100) if celkem_polozek > 0 else 0
    trend_celkem = sum(trend_kategorie.get(kod, {}).get('trend_kusy', 0) for kod in agregace) if trend_kategorie else 0
    trend_celkem_pct = round((trend_celkem / celkem_polozek * 100), 1) if celkem_polozek and trend_kategorie else None
    celkem_dnes = sum(plneni_dnes.get(kod, 0) for kod in agregace)

    return Response({
        'rok': rok,
        'mesic': mesic,
        'mesic_nazev': NAZVY_MESICU.get(mesic, ''),
        'celkem_polozek': celkem_polozek,
        'celkem_castka': str(celkem_castka),
        'kategorie': kategorie,
        'pracovnich_dni': pracovnich_dni,
        'smen_dnes': smen_dnes,
        'plneni': {
            'celkem_skutecne': celkem_skutecne,
            'celkem_dnes': celkem_dnes,
            'plneni_procent': round(plneni_celkem_pct, 1),
            'trend_kusy': trend_celkem if je_aktualni_mesic and trend_kategorie else None,
            'trend_procent': trend_celkem_pct,
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plany_prehled(request):
    """Přehled všech měsíců s aktivním plánem (pro timeline)."""
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    plany = PlanMonth.objects.filter(je_aktualni=True).order_by('-rok', '-mesic')
    return Response([
        {
            'id': p.id,
            'rok': p.rok,
            'mesic': p.mesic,
            'mesic_nazev': NAZVY_MESICU.get(p.mesic, ''),
            'cislo_verze': p.cislo_verze,
            'castka_celkem': str(p.castka_celkem),
            'vytvoreno_kdy': p.vytvoreno_kdy.isoformat(),
        }
        for p in plany
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_verze_detail(request, verze_id):
    """Vrátí detail konkrétní verze plánu."""
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    from django.shortcuts import get_object_or_404
    verze = get_object_or_404(PlanMonth, id=verze_id)
    return Response(serialize_plan(verze))


def _serialize_plan_prodejce(pp):
    """Serializuje PlanProdejce včetně kategorií."""
    return {
        'id': pp.id,
        'uzivatel_id': pp.uzivatel_id,
        'jmeno': pp.uzivatel.jmeno,
        'prijmeni': pp.uzivatel.prijmeni,
        'kategorie': {
            k.kategorie_kod: {
                'pocet_kusu': k.pocet_kusu,
                'castka': str(k.castka),
            }
            for k in pp.kategorie.all()
        },
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_prodejci(request, plan_prodejna_id):
    """
    GET – Vrátí plány prodejců pro danou prodejnu + seznam prodejců na prodejně + plán prodejny/kategorie.
    """
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    from django.shortcuts import get_object_or_404
    ps = get_object_or_404(PlanStore.objects.select_related('prodejna', 'plan_mesic').prefetch_related('kategorie'), id=plan_prodejna_id)

    # Prodejci domovské prodejny (aktivní) – nahoře v dropdownu
    prodejci_domovska = list(WebUser.objects.filter(prodejna_id=ps.prodejna_id, aktivni=True).order_by('jmeno', 'prijmeni'))
    # Ostatní aktivní prodejci (mohou pomáhat na více prodejnách)
    ids_domovska = {u.id for u in prodejci_domovska}
    prodejci_ostatni = list(WebUser.objects.filter(aktivni=True).exclude(id__in=ids_domovska).order_by('jmeno', 'prijmeni'))

    # Existující plány prodejců
    plany_pp = PlanProdejce.objects.filter(plan_prodejna=ps).prefetch_related('kategorie').select_related('uzivatel')

    # Kategorie plánu prodejny (pro referenci)
    kategorie_prodejny = [
        {
            'kategorie_kod': k.kategorie_kod,
            'kategorie_nazev': KATEGORIE_NAZVY.get(k.kategorie_kod, k.kategorie_kod),
            'castka_kategorie': str(k.castka_kategorie),
            'prumerna_cena_za_kus': str(k.prumerna_cena_za_kus) if k.prumerna_cena_za_kus else None,
            'pocet_kusu_plan': math.ceil(float(k.castka_kategorie) / float(k.prumerna_cena_za_kus))
                if k.prumerna_cena_za_kus and k.prumerna_cena_za_kus > 0 else None,
        }
        for k in ps.kategorie.all()
    ]

    # Součty přiděleného plánu per kategorie
    prideleno = {}
    for pp in plany_pp:
        for k in pp.kategorie.all():
            prideleno[k.kategorie_kod] = prideleno.get(k.kategorie_kod, 0) + k.pocet_kusu

    return Response({
        'plan_prodejna_id': ps.id,
        'prodejna_id': ps.prodejna_id,
        'prodejna_nazev': ps.prodejna.nazev,
        'rok': ps.plan_mesic.rok,
        'mesic': ps.plan_mesic.mesic,
        'castka_prodejna': str(ps.castka_prodejna),
        'kategorie_prodejny': kategorie_prodejny,
        'prideleno_kusu': prideleno,
        'prodejci_domovska': [{'id': u.id, 'jmeno': u.jmeno, 'prijmeni': u.prijmeni} for u in prodejci_domovska],
        'prodejci_ostatni': [{'id': u.id, 'jmeno': u.jmeno, 'prijmeni': u.prijmeni} for u in prodejci_ostatni],
        'plany_prodejcu': [_serialize_plan_prodejce(pp) for pp in plany_pp],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def plan_prodejci_ulozit(request, plan_prodejna_id):
    """
    POST – Uloží plány prodejců pro danou prodejnu.
    Tělo: { prodejci: [{uzivatel_id, kategorie: {KOD: {pocet_kusu, castka}}}] }
    """
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    from django.shortcuts import get_object_or_404
    ps = get_object_or_404(PlanStore, id=plan_prodejna_id)
    data = request.data.get('prodejci', [])

    with transaction.atomic():
        # Smazat existující plány prodejců pro tuto prodejnu
        PlanProdejce.objects.filter(plan_prodejna=ps).delete()

        for p_data in data:
            uzivatel_id = p_data.get('uzivatel_id')
            if not uzivatel_id:
                continue
            try:
                uzivatel = WebUser.objects.get(id=uzivatel_id)
            except WebUser.DoesNotExist:
                continue

            pp = PlanProdejce.objects.create(plan_prodejna=ps, uzivatel=uzivatel)

            for kod, hodnoty in p_data.get('kategorie', {}).items():
                pocet = int(hodnoty.get('pocet_kusu', 0))
                castka = Decimal(str(hodnoty.get('castka', 0)))
                if pocet > 0 or castka > 0:
                    PlanProdejceKategorie.objects.create(
                        plan_prodejce=pp,
                        kategorie_kod=kod,
                        pocet_kusu=pocet,
                        castka=castka,
                    )

    # Vrátit aktualizovaný stav
    ps_fresh = get_object_or_404(PlanStore.objects.prefetch_related('kategorie'), id=plan_prodejna_id)
    plany_pp = PlanProdejce.objects.filter(plan_prodejna=ps).prefetch_related('kategorie').select_related('uzivatel')
    prideleno = {}
    for pp in plany_pp:
        for k in pp.kategorie.all():
            prideleno[k.kategorie_kod] = prideleno.get(k.kategorie_kod, 0) + k.pocet_kusu

    return Response({
        'plany_prodejcu': [_serialize_plan_prodejce(pp) for pp in plany_pp],
        'prideleno_kusu': prideleno,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_plneni(request, rok, mesic):
    """
    Vrátí plnění plánu vs. realita z WEB_PRODEJE_ALL pro daný měsíc.
    Pro aktuální plán spočítá skutečné obraty a kusy a vrátí je spolu s plánem.
    """
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    from datetime import date as date_type
    from .plneni import plneni_firma, plneni_firma_do_data, plneni_prodejny, plneni_prodejny_do_data, plneni_celkem_firma
    import calendar

    # Aktuální plán pro měsíc
    plan = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
    if not plan:
        return Response({
            'plan': None,
            'plneni': None,
            'error': 'Pro tento měsíc neexistuje aktivní plán.',
        })

    # Skutečná data z WEB_PRODEJE_ALL
    celkem = plneni_celkem_firma(rok, mesic)
    kategorie_firma = plneni_firma(rok, mesic)
    prodejny_data = plneni_prodejny(rok, mesic)

    # Sestavení odpovědi
    plan_serialized = serialize_plan(plan)
    castka_plan = Decimal(str(plan.castka_celkem))
    obrat_skutecny = celkem['obrat']

    # Procenta plnění (obrat)
    pct_firma = 0
    if castka_plan and castka_plan > 0:
        pct_firma = float(obrat_skutecny / castka_plan * 100)

    dnes = date_type.today()
    je_aktualni_mesic = (rok == dnes.year and mesic == dnes.month)
    trend_firma = None
    trend_kategorie = {}
    trend_prodejny = {}

    if je_aktualni_mesic:
        prvni_den = date_type(rok, mesic, 1)
        pocet_dni = (dnes - prvni_den).days + 1
        dni_v_mesici = calendar.monthrange(rok, mesic)[1]
        if pocet_dni >= 2:
            kategorie_do_dnes = plneni_firma_do_data(rok, mesic, dnes)
            prodejny_do_dnes = plneni_prodejny_do_data(rok, mesic, dnes)
            # Trend firmy: obrat (plán je v obratu)
            prumer_obrat_den = float(obrat_skutecny) / pocet_dni
            trend_obrat = prumer_obrat_den * dni_v_mesici
            trend_firma_pct = (trend_obrat / float(castka_plan) * 100) if castka_plan else 0
            trend_firma = {'trend_obrat': round(trend_obrat, 2), 'trend_procent': round(trend_firma_pct, 1)}
            for kod, data in kategorie_do_dnes.items():
                kusy_d = data['kusy']
                prumer_k = kusy_d / pocet_dni if pocet_dni else 0
                trend_kategorie[kod] = round(prumer_k * dni_v_mesici)
            for pid, pd in prodejny_do_dnes.items():
                plan_ps = next((x for x in plan.prodejny.all() if x.prodejna_id == pid), None)
                if not plan_ps:
                    continue
                plan_obrat_p = float(plan_ps.castka_prodejna)
                skut_obrat_p = float(pd['obrat'])
                prumer_o = skut_obrat_p / pocet_dni if pocet_dni else 0
                trend_o = prumer_o * dni_v_mesici
                trend_pct_p = (trend_o / plan_obrat_p * 100) if plan_obrat_p > 0 else 0
                trend_prodejny[pid] = {
                    'trend_obrat': round(trend_o, 2),
                    'trend_procent': round(trend_pct_p, 1),
                    'kategorie': {},
                }
                for pk in plan_ps.kategorie.all():
                    kod = pk.kategorie_kod
                    plan_k = math.ceil(float(pk.castka_kategorie) / float(pk.prumerna_cena_za_kus or 1)) if pk.prumerna_cena_za_kus else 0
                    skut_k = pd['kategorie'].get(kod, {'kusy': 0})
                    kusy_k = skut_k['kusy']
                    prumer_k = kusy_k / pocet_dni if pocet_dni else 0
                    trend_k = round(prumer_k * dni_v_mesici)
                    trend_pct_k = (trend_k / plan_k * 100) if plan_k > 0 else 0
                    trend_prodejny[pid]['kategorie'][kod] = {
                        'trend_kusy': trend_k,
                        'trend_procent': round(trend_pct_k, 1),
                    }

    plneni = {
        'firma': {
            'plan_obrat': str(castka_plan),
            'skutecny_obrat': str(obrat_skutecny),
            'skutecne_kusy': celkem['kusy'],
            'plneni_procent': round(pct_firma, 1),
            'trend_obrat': trend_firma['trend_obrat'] if trend_firma else None,
            'trend_procent': trend_firma['trend_procent'] if trend_firma else None,
        },
        'kategorie': {},
        'prodejny': {},
    }

    # Kategorie na úrovni firmy – plán sčítáme z prodejen, skutečnost bereme 1× z kategorie_firma
    for ps in plan.prodejny.select_related('prodejna').prefetch_related('kategorie'):
        for pk in ps.kategorie.all():
            kod = pk.kategorie_kod
            plan_obrat = float(pk.castka_kategorie)
            plan_kusy = math.ceil(float(pk.castka_kategorie) / float(pk.prumerna_cena_za_kus or 1)) if pk.prumerna_cena_za_kus else 0
            if kod not in plneni['kategorie']:
                plneni['kategorie'][kod] = {
                    'plan_obrat': 0,
                    'plan_kusy': 0,
                    'skutecny_obrat': 0,
                    'skutecne_kusy': 0,
                    'plneni_procent': 0,
                    'trend_kusy': None,
                    'trend_procent': None,
                }
            plneni['kategorie'][kod]['plan_obrat'] += plan_obrat
            plneni['kategorie'][kod]['plan_kusy'] += plan_kusy

    # Skutečnost na úrovni firmy – 1× per kategorie (ne sčítat v cyklu přes prodejny)
    for kod, d in plneni['kategorie'].items():
        skutecne = kategorie_firma.get(kod, {'obrat': Decimal('0'), 'kusy': 0})
        d['skutecny_obrat'] = float(skutecne['obrat'])
        d['skutecne_kusy'] = skutecne['kusy']
        if d['plan_obrat'] > 0:
            d['plneni_procent'] = round(d['skutecny_obrat'] / d['plan_obrat'] * 100, 1)
        if kod in trend_kategorie and d['plan_kusy'] > 0:
            d['trend_kusy'] = trend_kategorie[kod]
            d['trend_procent'] = round(trend_kategorie[kod] / d['plan_kusy'] * 100, 1)
        d['plan_obrat'] = round(d['plan_obrat'], 2)
        d['skutecny_obrat'] = round(d['skutecny_obrat'], 2)

    # Prodejny
    for ps in plan.prodejny.select_related('prodejna').prefetch_related('kategorie'):
        pid = ps.prodejna_id
        pd = prodejny_data.get(pid, {'obrat': Decimal('0'), 'kusy': 0, 'kategorie': {}})
        plan_obrat_prod = float(ps.castka_prodejna)
        skut_obrat_prod = float(pd['obrat'])
        pct_prod = (skut_obrat_prod / plan_obrat_prod * 100) if plan_obrat_prod > 0 else 0

        td = trend_prodejny.get(pid, {})
        plneni['prodejny'][pid] = {
            'plan_obrat': round(plan_obrat_prod, 2),
            'skutecny_obrat': round(skut_obrat_prod, 2),
            'skutecne_kusy': pd['kusy'],
            'plneni_procent': round(pct_prod, 1),
            'trend_obrat': td.get('trend_obrat'),
            'trend_procent': td.get('trend_procent'),
            'kategorie': {},
        }
        for pk in ps.kategorie.all():
            kod = pk.kategorie_kod
            plan_obrat_k = float(pk.castka_kategorie)
            plan_kusy_k = math.ceil(float(pk.castka_kategorie) / float(pk.prumerna_cena_za_kus or 1)) if pk.prumerna_cena_za_kus else 0
            skut_k = pd['kategorie'].get(kod, {'obrat': Decimal('0'), 'kusy': 0})
            skut_obrat_k = float(skut_k['obrat'])
            skut_kusy_k = skut_k['kusy']
            pct_k = (skut_obrat_k / plan_obrat_k * 100) if plan_obrat_k > 0 else 0
            td_k = td.get('kategorie', {}).get(kod, {})
            plneni['prodejny'][pid]['kategorie'][kod] = {
                'plan_obrat': round(plan_obrat_k, 2),
                'plan_kusy': plan_kusy_k,
                'skutecny_obrat': round(skut_obrat_k, 2),
                'skutecne_kusy': skut_kusy_k,
                'plneni_procent': round(pct_k, 1),
                'trend_kusy': td_k.get('trend_kusy'),
                'trend_procent': td_k.get('trend_procent'),
            }

    return Response({
        'plan': plan_serialized,
        'plneni': plneni,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_plneni_prodejci(request, rok, mesic):
    """
    Vrátí plnění plánu pro všechny prodejce, kteří mají nastavený plán v daném měsíci.
    Stejná struktura jako plnění prodejen – prodejce = prodejna, kategorie pod ním.
    """
    if request.user.role != 'ADMIN':
        return Response({'error': 'Přístup pouze pro administrátory.'}, status=status.HTTP_403_FORBIDDEN)

    from datetime import date as date_type
    from .plneni import (
        plneni_prodejce_s_detailem,
        plneni_prodejce_do_data,
        plneni_prodejce_obrat_do_data,
    )
    import calendar

    plan = PlanMonth.objects.filter(rok=rok, mesic=mesic, je_aktualni=True).first()
    if not plan:
        return Response({
            'prodejci': [],
            'error': 'Pro tento měsíc neexistuje aktivní plán.',
        })

    # Sběr všech prodejců s plánem (agregace přes více prodejen)
    prodejci_plan = {}
    for ps in plan.prodejny.select_related('prodejna').prefetch_related('plany_prodejcu__kategorie'):
        for pp in ps.plany_prodejcu.select_related('uzivatel').prefetch_related('kategorie'):
            uid = pp.uzivatel_id
            if uid not in prodejci_plan:
                prodejci_plan[uid] = {
                    'uzivatel': pp.uzivatel,
                    'prodejny': [],
                    'kategorie': {},
                    'plan_obrat': Decimal('0'),
                    'plan_kusy': 0,
                }
            prodejci_plan[uid]['prodejny'].append(ps.prodejna.nazev)
            for k in pp.kategorie.all():
                kod = k.kategorie_kod
                if kod not in prodejci_plan[uid]['kategorie']:
                    prodejci_plan[uid]['kategorie'][kod] = {'pocet_kusu': 0, 'castka': Decimal('0')}
                prodejci_plan[uid]['kategorie'][kod]['pocet_kusu'] += k.pocet_kusu
                prodejci_plan[uid]['kategorie'][kod]['castka'] += k.castka
                prodejci_plan[uid]['plan_obrat'] += k.castka
                prodejci_plan[uid]['plan_kusy'] += k.pocet_kusu

    dnes = date_type.today()
    je_aktualni_mesic = (rok == dnes.year and mesic == dnes.month)
    pocet_dni = 0
    dni_v_mesici = 31
    if je_aktualni_mesic:
        prvni_den = date_type(rok, mesic, 1)
        pocet_dni = (dnes - prvni_den).days + 1
        dni_v_mesici = calendar.monthrange(rok, mesic)[1]

    result = []
    for uid, data in prodejci_plan.items():
        skutecne = plneni_prodejce_s_detailem(rok, mesic, uid)
        skut_obrat = skutecne['obrat']
        plan_obrat = data['plan_obrat']
        pct_obrat = float(skut_obrat / plan_obrat * 100) if plan_obrat and plan_obrat > 0 else 0

        trend_obrat = None
        trend_procent = None
        trend_kategorie = {}
        if je_aktualni_mesic and pocet_dni >= 2:
            obrat_do_dnes = plneni_prodejce_obrat_do_data(rok, mesic, dnes, uid)
            prumer_den = float(obrat_do_dnes) / pocet_dni
            trend_obrat = round(prumer_den * dni_v_mesici, 2)
            trend_procent = round((trend_obrat / float(plan_obrat) * 100), 1) if plan_obrat else 0
            kusy_do_dnes = plneni_prodejce_do_data(rok, mesic, dnes, uid)
            for kod, kusy_d in kusy_do_dnes.items():
                prumer_k = kusy_d / pocet_dni if pocet_dni else 0
                trend_kategorie[kod] = round(prumer_k * dni_v_mesici)

        kategorie_list = []
        for kod, plan_kat in data['kategorie'].items():
            plan_k = plan_kat['pocet_kusu']
            plan_c = float(plan_kat['castka'])
            skut_kat = skutecne['kategorie'].get(kod, {'obrat': Decimal('0'), 'kusy': 0})
            skut_k = skut_kat['kusy']
            pct_k = (skut_k / plan_k * 100) if plan_k > 0 else 0
            trend_k = trend_kategorie.get(kod)
            trend_pct_k = round((trend_k / plan_k * 100), 1) if plan_k and trend_k is not None else None
            kategorie_list.append({
                'kategorie_kod': kod,
                'kategorie_nazev': KATEGORIE_NAZVY.get(kod, kod),
                'plan_kusy': plan_k,
                'plan_castka': round(plan_c, 2),
                'skutecne_kusy': skut_k,
                'skutecny_obrat': round(float(skut_kat['obrat']), 2),
                'plneni_procent': round(pct_k, 1),
                'trend_kusy': trend_k,
                'trend_procent': trend_pct_k,
            })

        skut_kusy_celkem = sum(s['kusy'] for s in skutecne['kategorie'].values())
        plan_kusy_celkem = data['plan_kusy']
        pct_kusy = round((skut_kusy_celkem / plan_kusy_celkem * 100), 1) if plan_kusy_celkem else 0
        trend_kusy_celkem = round(sum(trend_kategorie.values())) if trend_kategorie else None
        trend_procent_kusy = round((trend_kusy_celkem / plan_kusy_celkem * 100), 1) if plan_kusy_celkem and trend_kusy_celkem is not None else None

        result.append({
            'prodejce_id': uid,
            'jmeno': data['uzivatel'].jmeno,
            'prijmeni': data['uzivatel'].prijmeni,
            'prodejna_nazev': ', '.join(sorted(set(data['prodejny']))),
            'plan_obrat': round(float(plan_obrat), 2),
            'plan_kusy': plan_kusy_celkem,
            'skutecny_obrat': round(float(skut_obrat), 2),
            'skutecne_kusy': skut_kusy_celkem,
            'plneni_procent': round(pct_obrat, 1),
            'plneni_procent_kusy': pct_kusy,
            'trend_obrat': trend_obrat,
            'trend_procent': trend_procent,
            'trend_kusy': trend_kusy_celkem,
            'trend_procent_kusy': trend_procent_kusy,
            'kategorie': kategorie_list,
        })

    # Seřadit podle příjmení, jména
    result.sort(key=lambda x: (x['prijmeni'], x['jmeno']))

    return Response({'prodejci': result})
