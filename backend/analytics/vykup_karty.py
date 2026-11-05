"""Nedokončené karty výkupů.

Druhý den po výkupu (výkup v pondělí, kontrola ve středu ráno) vznikne úkol,
pokud karta není hotová a kus je volně skladem. Rezervace s 0 volnými kusy
se nepočítá. Prvního dne v měsíci jde Radkovi Bulandrovi souhrn za minulý měsíc.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from orders.slack_recipients import MARKOVIC_WEB_USER_ID, bulandra_slack_id
from tasks.models import Ukol
from tasks.slack_notify import send_slack_dm, slack_user_id_for_web_user
from tasks.task_create_service import create_ukol_for_user
from users.models import WebUser

from .models import VykupKartaStav, VykupKartyHlaseni, WebVykupy

UKOL_NAZEV = 'Chybějící karty'
VYSLEDEK = 'Dodělat karty k výkupům, jinak se odečítají z výplaty'
POPIS_UKOLU = (
    'Každý řádek je jeden telefon. Doplň fotky, parametry, krátký popis a popis '
    'a kartu aktivuj, ať je vidět na webu.'
)
POPIS_MIN_ZNAKU = 80
DEADLINE_CAS = time(15, 0)
DNI_PO_VYKUPU = 2
MESICE = (
    '', 'leden', 'únor', 'březen', 'duben', 'květen', 'červen',
    'červenec', 'srpen', 'září', 'říjen', 'listopad', 'prosinec',
)
KOD_RE = re.compile(r'\bV\d{5,}\b')


def parse_skladem(text: str) -> tuple[int, int]:
    """Vrátí (ks celkem, ks volné). Bez zmínky o rezervaci jsou volné = celkem."""
    raw = re.sub(r'\s+', ' ', text or '').strip()
    total = re.search(r'(\d+)\s*ks', raw, re.IGNORECASE)
    ks = int(total.group(1)) if total else 0
    free = re.search(r'(\d+)\s*ks\s*voln', raw, re.IGNORECASE)
    volne = int(free.group(1)) if free else ks
    return ks, volne


def karta_je_hotova(karta: dict) -> bool:
    """Fotky, vyplněné parametry a popis. Obrázek v popisu platí jako popis."""
    if not karta.get('nalezeno'):
        return False
    if int(karta.get('photos') or 0) <= 0:
        return False
    if int(karta.get('params') or 0) <= 0:
        return False
    if int(karta.get('popis_text_len') or 0) > POPIS_MIN_ZNAKU or karta.get('popis_ma_obrazek'):
        return True
    return False


def je_volne_skladem(karta: dict) -> bool:
    if 'stock_text' in karta and karta.get('volne') is None:
        _, volne = parse_skladem(karta.get('stock_text') or '')
        return volne > 0
    return int(karta.get('volne') or 0) > 0


def po_druhem_dni(vystaveno: date, dnes: date) -> bool:
    return (dnes - vystaveno).days >= DNI_PO_VYKUPU


def mesic_pred(dnes: date) -> str:
    prvni = dnes.replace(day=1)
    pred = prvni - timedelta(days=1)
    return pred.strftime('%Y-%m')


def _normalizuj_kartu(karta: dict) -> dict:
    out = dict(karta)
    if out.get('stock_text'):
        ks, volne = parse_skladem(out['stock_text'])
        out['ks'] = ks
        out['volne'] = volne
    elif out.get('volne') is None:
        out['volne'] = 0
    return out


def admin_url(karta: dict) -> str:
    cat = karta.get('cat') or ''
    zbozi = karta.get('zbozi_id') or ''
    if not cat or not zbozi:
        return ''
    return f'https://www.mobilmajak.cz/admin/kategorie-{cat}/zbozi-{zbozi}'


def dod_text(vykup, karta: dict) -> str:
    nazev = (karta.get('nazev') or getattr(vykup, 'nazev', '') or '').strip()
    kod = getattr(vykup, 'kod', '') or karta.get('kod')
    url = admin_url(karta)
    line = f'{nazev} ({kod})'.strip()
    if url:
        line = f'{line} {url}'
    return line


def kody_v_otevrenych_ukolech() -> dict[str, int]:
    nalezene: dict[str, int] = {}
    qs = Ukol.objects.filter(ukol=UKOL_NAZEV, stav__in=Ukol.ACTIVE_STAVY).only('id', 'dod_polozky')
    for task in qs:
        for item in task.dod_polozky or []:
            match = KOD_RE.search(item.get('text') or '')
            if match:
                nalezene[match.group(0)] = task.id
    for row in VykupKartaStav.objects.exclude(ukol_id=None).only('kod', 'ukol_id'):
        nalezene.setdefault(row.kod, row.ukol_id)
    return nalezene


def deadline_pro_uzivatele(user_id: int, dnes: date, ted: datetime) -> date:
    """Nejbližší pracovní směna v 15:00. Po patnácté hodině už ne dnes."""
    cas = timezone.localtime(ted).time() if timezone.is_aware(ted) else ted.time()
    od = dnes + timedelta(days=1) if cas >= DEADLINE_CAS else dnes
    do = dnes + timedelta(days=14)
    from shifts.models import Smena

    smena = (
        Smena.objects.filter(
            user_id=user_id,
            aktivni=True,
            typ_smeny='prace',
            datum__gte=od,
            datum__lte=do,
        )
        .order_by('datum', 'cas_od')
        .first()
    )
    if smena:
        return smena.datum
    return dnes + timedelta(days=DNI_PO_VYKUPU)


def format_hlaseni(mesic: str, polozky: list[dict]) -> str:
    rok, mes = mesic.split('-')
    nazev = f'{MESICE[int(mes)]} {rok}'
    podle = defaultdict(list)
    for item in polozky:
        podle[item['prodejce']].append(item)
    lines = [f'Nedokončené karty výkupů za {nazev}', '']
    for jmeno in sorted(podle, key=lambda n: (-len(podle[n]), n)):
        lines.append(f'{jmeno}: {len(podle[jmeno])}')
    lines.append(f'Celkem: {len(polozky)}')
    lines.append('')
    lines.append('Provizi za výkup z těchto karet lze odečíst z výplaty:')
    for item in sorted(polozky, key=lambda x: (x['prodejce'], x['kod'])):
        odkaz = f" {item['url']}" if item.get('url') else ''
        lines.append(f"• {item['kod']} {item['nazev']} — {item['prodejce']}{odkaz}")
    return '\n'.join(lines)


def _uloz_stav(karta: dict, *, hotovo: bool, skladem: bool, ukol_id: int | None = None) -> None:
    kod = karta.get('kod')
    if not kod:
        return
    row, _ = VykupKartaStav.objects.get_or_create(kod=kod)
    row.hotovo = hotovo
    row.skladem = skladem
    row.zbozi_id = str(karta.get('zbozi_id') or row.zbozi_id or '')
    row.kategorie_id = str(karta.get('cat') or row.kategorie_id or '')
    if ukol_id:
        row.ukol_id = ukol_id
    row.save()


def _otevreny_ukol(user_id: int, creator_id: int) -> Ukol | None:
    return (
        Ukol.objects.filter(
            ukol=UKOL_NAZEV,
            id_prodejce_ukol=user_id,
            id_prodejce_zadal=creator_id,
            stav__in=Ukol.ACTIVE_STAVY,
        )
        .order_by('-id')
        .first()
    )


def _pridej_do_ukolu(task: Ukol, texts: list[str], deadline: date, dnes: date) -> None:
    dod = list(task.dod_polozky or [])
    for text in texts:
        dod.append({'text': text, 'splneno': False})
    task.dod_polozky = dod
    if task.deadline is None or task.deadline < dnes:
        task.deadline = deadline
        task.deadline_cas = DEADLINE_CAS
    task.save(update_fields=['dod_polozky', 'deadline', 'deadline_cas', 'upraveno'])


def _slack_uzivateli(user_id: int, text: str) -> bool:
    user = WebUser.objects.filter(pk=user_id, aktivni=True).first()
    slack_id = slack_user_id_for_web_user(user) if user else None
    if not slack_id:
        return False
    return bool(send_slack_dm(slack_id, text))


def _vytvor_nebo_dopln(creator, user_id: int, store_id: int | None, texts: list[str], dnes: date, ted: datetime):
    deadline = deadline_pro_uzivatele(user_id, dnes, ted)
    task = _otevreny_ukol(user_id, creator.id)
    if task:
        _pridej_do_ukolu(task, texts, deadline, dnes)
        _slack_uzivateli(
            user_id,
            'Do úkolu Chybějící karty přibyly karty výkupů:\n' + '\n'.join(texts),
        )
        return task, False
    payload = {
        'ukol': UKOL_NAZEV,
        'vysledek': VYSLEDEK,
        'popis': POPIS_UKOLU,
        'dod_polozky': [{'text': text, 'splneno': False} for text in texts],
        'priorita': 'vysoka',
        'typ': 'prirazeny',
        'termin_zadani': dnes.isoformat(),
        'deadline': deadline.isoformat(),
        'deadline_cas': DEADLINE_CAS.strftime('%H:%M'),
        'id_prodejce_ukol': user_id,
        'id_prodejce_zadal': creator.id,
        'id_prodejny': store_id,
    }
    vytvoreny, err = create_ukol_for_user(creator, payload)
    if err:
        raise RuntimeError(err)
    return vytvoreny, True


def zpracuj(*, dnes: date, ted: datetime, vykupy, karty: dict[str, dict], creator, hlasit_mesic: str | None, dry_run: bool = False) -> dict:
    """karty jsou surová měření ze Symplia. hlasit_mesic je YYYY-MM, nebo None."""
    karty = {kod: {**_normalizuj_kartu(k), 'kod': kod} for kod, k in karty.items()}
    otevrene = kody_v_otevrenych_ukolech()
    due = []
    for vykup in vykupy:
        kod = (getattr(vykup, 'kod', '') or '').strip()
        karta = karty.get(kod)
        if not karta or not karta.get('nalezeno'):
            continue
        hotovo = karta_je_hotova(karta)
        skladem = je_volne_skladem(karta)
        if not dry_run:
            _uloz_stav(karta, hotovo=hotovo, skladem=skladem)
        if hotovo or not skladem:
            continue
        if not po_druhem_dni(vykup.vystaveno, dnes):
            continue
        if not getattr(vykup, 'id_prodejce', None):
            continue
        if kod in otevrene:
            continue
        due.append(vykup)

    vytvorene = []
    doplnene = []
    chyby = []
    skupiny = defaultdict(list)
    for vykup in due:
        skupiny[vykup.id_prodejce].append(vykup)

    if not dry_run:
        for user_id, items in skupiny.items():
            user = WebUser.objects.filter(pk=user_id, aktivni=True).first()
            if not user:
                chyby.append(f'neaktivní prodejce {user_id}')
                continue
            store_id = next((i.id_prodejny for i in items if getattr(i, 'id_prodejny', None)), None)
            texts = [dod_text(i, karty[i.kod.strip()]) for i in sorted(items, key=lambda x: x.kod)]
            try:
                task, novy = _vytvor_nebo_dopln(creator, user_id, store_id, texts, dnes, ted)
            except RuntimeError as exc:
                chyby.append(f'{user_id}: {exc}')
                continue
            for item in items:
                _uloz_stav(karty[item.kod.strip()], hotovo=False, skladem=True, ukol_id=task.id)
            (vytvorene if novy else doplnene).append({'ukol_id': task.id, 'user_id': user_id, 'kody': [i.kod for i in items]})

    hlaseni = None
    if hlasit_mesic:
        hlaseni = _hlaseni_mesice(hlasit_mesic, vykupy, karty, dry_run=dry_run)

    return {
        'due': [v.kod for v in due],
        'vytvorene': vytvorene,
        'doplnene': doplnene,
        'chyby': chyby,
        'hlaseni': hlaseni,
    }


def _jmeno(user_id: int | None) -> str:
    if not user_id:
        return 'bez prodejce'
    user = WebUser.objects.filter(pk=user_id).first()
    if not user:
        return f'uživatel {user_id}'
    return f'{user.jmeno} {user.prijmeni}'.strip()


def _hlaseni_mesice(mesic: str, vykupy, karty: dict[str, dict], *, dry_run: bool) -> dict:
    if VykupKartyHlaseni.objects.filter(mesic=mesic).exists():
        return {'mesic': mesic, 'stav': 'uz_odeslano'}
    polozky = []
    for vykup in vykupy:
        kod = (vykup.kod or '').strip()
        if vykup.vystaveno.strftime('%Y-%m') != mesic:
            continue
        karta = karty.get(kod)
        if not karta or not karta.get('nalezeno'):
            continue
        if karta_je_hotova(karta) or not je_volne_skladem(karta):
            continue
        polozky.append({
            'kod': kod,
            'nazev': (karta.get('nazev') or vykup.nazev or '').strip(),
            'prodejce': _jmeno(getattr(vykup, 'id_prodejce', None)),
            'url': admin_url(karta),
        })
    text = format_hlaseni(mesic, polozky) if polozky else ''
    if dry_run:
        return {'mesic': mesic, 'stav': 'dry_run', 'pocet': len(polozky), 'text': text}
    if not polozky:
        VykupKartyHlaseni.objects.create(mesic=mesic, pocet=0, text='')
        return {'mesic': mesic, 'stav': 'prazdne', 'pocet': 0}
    slack_id = bulandra_slack_id()
    if not slack_id or not send_slack_dm(slack_id, text):
        return {'mesic': mesic, 'stav': 'slack_selhal', 'pocet': len(polozky), 'text': text}
    VykupKartyHlaseni.objects.create(mesic=mesic, pocet=len(polozky), text=text)
    return {'mesic': mesic, 'stav': 'odeslano', 'pocet': len(polozky)}


def kody_ke_kontrole(dnes: date) -> list:
    hotove = set(VykupKartaStav.objects.filter(hotovo=True).values_list('kod', flat=True))
    hranice = dnes - timedelta(days=DNI_PO_VYKUPU)
    prvni = dnes.replace(day=1)
    start = prvni
    if dnes.day == 1:
        start = (prvni - timedelta(days=1)).replace(day=1)
    qs = (
        WebVykupy.objects.filter(vystaveno__gte=start, vystaveno__lte=hranice)
        .exclude(kod__isnull=True)
        .exclude(kod='')
        .order_by('kod', 'id')
    )
    vybrane = {}
    for row in qs:
        kod = (row.kod or '').strip()
        if not kod or kod in hotove or kod in vybrane:
            continue
        vybrane[kod] = row
    return list(vybrane.values())


def nacti_karty_ze_symplia(kody: list[str]) -> list[dict]:
    if not kody:
        return []
    script = Path(settings.BASE_DIR).parent / 'scripts' / 'vykup-karty' / 'check.js'
    if not script.is_file():
        raise FileNotFoundError(script)
    env = os.environ.copy()
    node_modules = Path(settings.BASE_DIR).parent / 'scripts' / 'vykupy-actor' / 'node_modules'
    env['NODE_PATH'] = str(node_modules)
    proc = subprocess.run(
        ['node', str(script)],
        input=json.dumps({'kody': kody}),
        capture_output=True,
        text=True,
        timeout=45 * 60,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or '').strip()
        raise RuntimeError(detail or f'check.js skončil kódem {proc.returncode}')
    return json.loads(proc.stdout or '[]')


def spustit(*, dnes: date | None = None, ted: datetime | None = None, dry_run: bool = False, stdout=None) -> dict:
    ted = ted or timezone.now()
    dnes = dnes or timezone.localdate(ted)
    log = stdout.write if stdout else print
    creator = WebUser.objects.filter(pk=MARKOVIC_WEB_USER_ID, aktivni=True).first()
    if not creator:
        raise RuntimeError('Chybí aktivní uživatel Markovič (id 999) jako zadavatel úkolů.')
    vykupy = kody_ke_kontrole(dnes)
    log(f'Ke kontrole {len(vykupy)} karet (stav ke dni {dnes.isoformat()}).\n')
    karty = nacti_karty_ze_symplia([(v.kod or '').strip() for v in vykupy]) if vykupy else []
    podle = { (k.get('kod') or '').strip(): k for k in karty }
    hlasit = mesic_pred(dnes) if dnes.day == 1 else None
    vysledek = zpracuj(
        dnes=dnes,
        ted=ted,
        vykupy=vykupy,
        karty=podle,
        creator=creator,
        hlasit_mesic=hlasit,
        dry_run=dry_run,
    )
    log(
        f"Úkoly nové {len(vysledek['vytvorene'])}, doplněné {len(vysledek['doplnene'])}, "
        f"k řešeni {len(vysledek['due'])}.\n"
    )
    if vysledek['chyby']:
        log('Chyby: ' + '; '.join(vysledek['chyby']) + '\n')
    if vysledek['hlaseni']:
        log(f"Hlášení {vysledek['hlaseni']}.\n")
    return vysledek
