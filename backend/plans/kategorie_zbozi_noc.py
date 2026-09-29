"""Noční ověření odškrtnutých kódů proti exportu Symplia."""
from __future__ import annotations

import json
import os
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone

from stores.models import Prodejna
from stores.oteviraci_doba_utils import opening_window_for_date

from .kategorie_zbozi import aplikuj_vysledek, cekajici_claimy

MAX_DNU_ZA_NOC = 7
LOCKY = (
    ('/tmp/prodeje-actor.lock', '/tmp/prodeje-actor.pid'),
    ('/tmp/vykupy-actor.lock', '/tmp/vykupy-actor.pid'),
    ('/tmp/sklad-vydejky-actor.lock', '/tmp/sklad-vydejky-actor.pid'),
)
PRODEJE_LOCK = '/tmp/prodeje-actor.lock'
PRODEJE_PID = '/tmp/prodeje-actor.pid'
CEKANI_LOCK_S = 20 * 60


def _pid_zije(pid_path: str) -> bool:
    if not os.path.exists(pid_path):
        return False
    try:
        pid = int(Path(pid_path).read_text().strip())
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def actor_bezi() -> bool:
    return any(_pid_zije(pid) for _, pid in LOCKY)


def pockej_na_actory(limit_s: int = CEKANI_LOCK_S) -> bool:
    deadline = time.monotonic() + limit_s
    while actor_bezi():
        if time.monotonic() >= deadline:
            return False
        time.sleep(15)
    return True


def drz_prodeje_lock():
    """Zapíše lock prodejního actoru s PID tohoto procesu. Actor běh přeskočí."""
    Path(PRODEJE_LOCK).write_text(str(os.getpid()))
    Path(PRODEJE_PID).write_text(str(os.getpid()))


def pust_prodeje_lock():
    try:
        current = Path(PRODEJE_PID).read_text().strip()
    except OSError:
        return
    if current != str(os.getpid()):
        return
    for path in (PRODEJE_LOCK, PRODEJE_PID):
        try:
            os.remove(path)
        except OSError:
            pass


def prodejny_zavrene(now=None) -> bool:
    now = now or timezone.now()
    tz = timezone.get_current_timezone()
    local = timezone.localtime(now, tz)
    latest = None
    for store in Prodejna.objects.filter(aktivni=True):
        window = opening_window_for_date(store.oteviraci_doba, local.date(), tz)
        if window and (latest is None or window[1] > latest):
            latest = window[1]
    if latest is None:
        return True
    return local >= latest + timedelta(minutes=30)


def posledni_den_prodeje(claim) -> str | None:
    from .plneni import _base_where_params

    start_d, end_d = _base_where_params(claim.rok, claim.mesic)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT MAX(DATE(Vystaveno))
            FROM WEB_PRODEJE_ALL
            WHERE TRIM(Kod) = %s
              AND Vystaveno >= %s AND Vystaveno < %s
            """,
            [claim.kod, start_d, end_d],
        )
        row = cursor.fetchone()
    den = row[0] if row else None
    if den is None:
        return None
    if isinstance(den, datetime):
        den = den.date()
    return den.isoformat()


def _compare_script() -> Path:
    raw = os.environ.get('SYMPLIO_COMPARE_JS')
    if raw:
        return Path(raw)
    return Path(settings.BASE_DIR).parent / 'scripts' / 'symplio-poznamka-fix' / 'compare.js'


def stahni_kategorie_dne(den: str, out_json: Path) -> dict:
    script = _compare_script()
    if not script.is_file():
        raise FileNotFoundError(f'Chybí {script}')
    out_json.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            'node', str(script),
            '--from', den, '--to', den,
            '--download',
            '--json-categories', str(out_json),
        ],
        check=True,
        timeout=240,
        cwd=str(script.parent),
    )
    return json.loads(out_json.read_text(encoding='utf-8'))


def spustit(*, stdout=None, force=False) -> dict:
    """Ověří čekající claimy. Bez force nespustí přes den ani při běhu actorů."""
    log = stdout.write if stdout else print
    if not force and not prodejny_zavrene():
        log('Prodejny ještě nejsou zavřené, kontrola se odkládá.\n')
        return {'stav': 'zavreno'}
    claimy = cekajici_claimy()
    if not claimy:
        log('Žádné odškrtnuté kódy.\n')
        return {'stav': 'prazdne'}
    if not force and not pockej_na_actory():
        log('Actor stále běží, kontrola se odkládá.\n')
        return {'stav': 'actor'}

    dny_claimu = defaultdict(list)
    for claim in claimy:
        den = posledni_den_prodeje(claim)
        if not den:
            aplikuj_vysledek(claim, '', '', chybi=True)
            continue
        dny_claimu[den].append(claim)

    vybrane = sorted(dny_claimu)[:MAX_DNU_ZA_NOC]
    if not vybrane:
        return {'stav': 'hotovo', 'potvrzeno': 0, 'nepotvrzeno': 0}

    potvrzeno = 0
    nepotvrzeno = 0
    drz_prodeje_lock()
    try:
        for den in vybrane:
            out = Path(settings.BASE_DIR) / 'tmp' / f'kategorie-zbozi-{den}.json'
            try:
                data = stahni_kategorie_dne(den, out)
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
                log(f'{den}: stažení selhalo ({exc}), kódy zůstanou ve frontě.\n')
                continue
            kody = data.get('kody') or {}
            konflikty = set(data.get('konflikty') or [])
            for claim in dny_claimu[den]:
                if claim.kod in konflikty:
                    stav = aplikuj_vysledek(claim, '', '', konflikt=True)
                elif claim.kod not in kody:
                    stav = aplikuj_vysledek(claim, '', '', chybi=True)
                else:
                    info = kody[claim.kod] or {}
                    stav = aplikuj_vysledek(
                        claim,
                        info.get('kategorie') or '',
                        info.get('kategorie_1') or '',
                        info.get('kategorie_2') or '',
                    )
                if stav == 'potvrzeno':
                    potvrzeno += 1
                elif stav == 'nepotvrzeno':
                    nepotvrzeno += 1
    finally:
        pust_prodeje_lock()

    zbyva = max(0, len(dny_claimu) - len(vybrane))
    log(f'Potvrzeno {potvrzeno}, nepotvrzeno {nepotvrzeno}, dnů odloženo {zbyva}.\n')
    return {
        'stav': 'hotovo',
        'potvrzeno': potvrzeno,
        'nepotvrzeno': nepotvrzeno,
        'dnu': len(vybrane),
        'odlozeno_dnu': zbyva,
    }
