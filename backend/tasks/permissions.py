from __future__ import annotations

from django.db.models import Q

from users.exclusions import get_excluded_report_user_ids, real_sales_staff_queryset
from users.models import WebUser
from users.vedouci_utils import is_task_manager, vedouci_store_ids

from .models import Ukol
from .urgency import wip_warning_for_assignee

# Účty nezobrazovat v seznamu přiřazení úkolů (case-insensitive jméno + příjmení).
_TASK_ASSIGNEE_EXCLUDED_NAME_PAIRS = frozenset({
    ('prodejce', 'prodejce'),
    ('administrátor', 'systémový'),
    ('administrator', 'systemovy'),
    ('administrátor', 'systemovy'),
    ('petr', 'valenta'),
})


def _normalize_name_pair(jmeno, prijmeni) -> tuple[str, str]:
    return (
        (jmeno or '').strip().lower(),
        (prijmeni or '').strip().lower(),
    )


def is_excluded_task_assignee(user: WebUser) -> bool:
    return _normalize_name_pair(user.jmeno, user.prijmeni) in _TASK_ASSIGNEE_EXCLUDED_NAME_PAIRS


def tasks_queryset_for_user(user):
    role = getattr(user, "role", None)
    personal = Q(id_prodejce_ukol=user.id) | (
        Q(typ="osobni") & Q(id_prodejce_zadal=user.id)
    )
    if role == "ADMIN":
        return Ukol.objects.all()
    store_ids = vedouci_store_ids(user)
    if store_ids:
        return Ukol.objects.filter(Q(id_prodejny__in=store_ids) | personal)
    return Ukol.objects.filter(personal)


def user_can_access_task(user, task: Ukol) -> bool:
    return tasks_queryset_for_user(user).filter(pk=task.pk).exists()


def user_can_edit_task_details(user, task: Ukol) -> bool:
    """Úprava textu, termínu, přiřazení – admin nebo vedoucí zadavatel."""
    role = getattr(user, "role", None)
    if role == "ADMIN":
        return True
    if not is_task_manager(user):
        return False
    if task.typ == "prirazeny":
        if task.id_prodejny and task.id_prodejny in vedouci_store_ids(user):
            return True
        return False
    return task.typ == "osobni" and task.id_prodejce_zadal == user.id


def user_can_approve_task(user, task: Ukol) -> bool:
    if not task.vyzaduje_schvaleni or task.stav != "ceka_schvaleni":
        return False
    return user_can_edit_task_details(user, task)


def _normalize_dod_polozky(raw) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        out.append({"text": text, "splneno": bool(item.get("splneno"))})
    return out


def _dod_complete(polozky) -> bool:
    normalized = _normalize_dod_polozky(polozky)
    return bool(normalized) and all(p["splneno"] for p in normalized)


def sync_ukol_from_vysledek(data: dict) -> None:
    vysledek = (data.get("vysledek") or data.get("ukol") or "").strip()
    if vysledek and not (data.get("ukol") or "").strip():
        data["ukol"] = vysledek.split("\n")[0][:255]
    elif vysledek:
        data.setdefault("ukol", vysledek.split("\n")[0][:255])


def validate_task_create(user, data: dict) -> str | None:
    typ = data.get("typ") or "osobni"
    if typ not in ("prirazeny", "osobni"):
        return "Neplatný typ úkolu."

    sync_ukol_from_vysledek(data)

    assignee_id = data.get("id_prodejce_ukol")
    store_id = data.get("id_prodejny")

    if typ == "prirazeny":
        vysledek = (data.get("vysledek") or data.get("ukol") or "").strip()
        if not vysledek:
            return "U přiřazeného úkolu je povinný výsledek (Outcome)."
        data["vysledek"] = vysledek

        dod = _normalize_dod_polozky(data.get("dod_polozky"))
        if len(dod) < 1:
            return "U přiřazeného úkolu je povinná alespoň jedna položka Definition of Done."
        data["dod_polozky"] = dod

        if not data.get("deadline"):
            return "U přiřazeného úkolu je povinný termín dokončení (deadline)."

        if not assignee_id:
            return "U přiřazeného úkolu je povinný přiřazený uživatel."
        try:
            assignee = WebUser.objects.get(id=int(assignee_id), aktivni=True)
        except (WebUser.DoesNotExist, TypeError, ValueError):
            return "Přiřazený uživatel neexistuje nebo není aktivní."

        role = getattr(user, "role", None)
        storeless = not store_id

        if storeless:
            if role != "ADMIN":
                return "Úkoly bez pobočky může vytvářet jen administrátor."
            if not _assignee_allowed_storeless(assignee):
                return "Uživatele nelze přiřadit k úkolu bez pobočky."
            data["id_prodejny"] = None
        else:
            if role == "ADMIN":
                pass
            elif is_task_manager(user):
                manager_stores = vedouci_store_ids(user)
                if int(store_id) not in manager_stores:
                    return "Nemáte oprávnění vytvářet úkoly na této prodejně."
                if not _assignee_allowed_on_store(assignee, int(store_id)):
                    return "Uživatele nelze přiřadit na tuto prodejnu."
            else:
                return "Nemáte oprávnění vytvářet přiřazené úkoly."
    else:
        if is_task_manager(user):
            pass
        else:
            data["id_prodejce_ukol"] = user.id
            data["id_prodejce_zadal"] = user.id
            data["id_prodejny"] = None

    priorita = data.get("priorita", "stredni")
    if priorita not in dict(Ukol.PRIORITY):
        return "Neplatná priorita."

    return None


def validate_task_update(user, task: Ukol, data: dict) -> str | None:
    typ = data.get("typ", task.typ)
    detail_keys = {"vysledek", "termin_zadani", "deadline", "id_prodejce_ukol", "id_prodejny", "typ", "ukol"}
    if typ == "prirazeny" and detail_keys & set(data.keys()):
        merged = {
            "typ": typ,
            "id_prodejny": data.get("id_prodejny", task.id_prodejny),
            "id_prodejce_ukol": data.get("id_prodejce_ukol", task.id_prodejce_ukol),
            "priorita": data.get("priorita", task.priorita),
            "vysledek": data.get("vysledek", task.vysledek),
            "ukol": data.get("ukol", task.ukol),
            "dod_polozky": data.get("dod_polozky", task.dod_polozky),
            "deadline": data.get("deadline", task.deadline),
        }
        err = validate_task_create(user, merged)
        if err:
            return err

    new_stav = data.get("stav", task.stav)
    if task.typ == "prirazeny" or typ == "prirazeny":
        err = _validate_prirazeny_state_change(user, task, data, new_stav)
        if err:
            return err

    if "dod_polozky" in data:
        data["dod_polozky"] = _normalize_dod_polozky(data["dod_polozky"])

    sync_ukol_from_vysledek(data)
    return None


def _validate_prirazeny_state_change(user, task: Ukol, data: dict, new_stav: str) -> str | None:
    if new_stav == "blokovany":
        duvod = (data.get("blokovano_duvod") or task.blokovano_duvod or "").strip()
        if not duvod:
            return "U blokovaného úkolu je povinný důvod."

    if new_stav in ("hotovo", "ceka_schvaleni"):
        dod = data.get("dod_polozky", task.dod_polozky)
        if not _dod_complete(dod):
            return "Před dokončením musí být splněny všechny položky Definition of Done."

        if new_stav == "hotovo" and task.vyzaduje_schvaleni:
            if task.stav == "ceka_schvaleni":
                if not user_can_approve_task(user, task):
                    return "Schválit může jen vedoucí."
            elif task.id_prodejce_ukol == user.id:
                data["stav"] = "ceka_schvaleni"
                return None

    return None


def wip_warning_on_assign(assignee_id) -> str | None:
    try:
        aid = int(assignee_id)
    except (TypeError, ValueError):
        return None
    return wip_warning_for_assignee(aid)


def user_can_edit_task(user, task: Ukol) -> bool:
    role = getattr(user, "role", None)
    if role == "ADMIN":
        return True
    if task.id_prodejny and task.id_prodejny in vedouci_store_ids(user):
        return True
    return task.id_prodejce_ukol == user.id or (
        task.typ == "osobni" and task.id_prodejce_zadal == user.id
    )


def _user_display(u: WebUser | None, skupina: str | None = None) -> dict | None:
    if not u:
        return None
    out = {
        "id": u.id,
        "jmeno": u.jmeno,
        "prijmeni": u.prijmeni,
        "jmeno_plne": f"{u.jmeno} {u.prijmeni}".strip(),
    }
    if skupina:
        out["skupina"] = skupina
    return out


def _assignee_allowed_on_store(assignee: WebUser, _store_id: int) -> bool:
    if not assignee.aktivni:
        return False
    if is_excluded_task_assignee(assignee):
        return False
    if assignee.role == "ADMIN":
        return True
    if assignee.role not in ("PRODEJCE", "VEDOUCI", "BRIGADNIK"):
        return False
    return assignee.id not in get_excluded_report_user_ids()


def _assignee_allowed_storeless(assignee: WebUser) -> bool:
    """Aktivní uživatelé pro úkoly bez pobočky – admin i prodejní role na libovolné prodejně."""
    if not assignee.aktivni or is_excluded_task_assignee(assignee):
        return False
    if assignee.role == "ADMIN":
        return True
    if assignee.role not in ("PRODEJCE", "VEDOUCI", "BRIGADNIK"):
        return False
    return assignee.id not in get_excluded_report_user_ids()


def _storeless_skupina(u: WebUser, store_names: dict[int, str]) -> tuple[str, dict]:
    extra = {}
    if u.role == "ADMIN":
        return "admini", extra
    if u.prodejna_id is None:
        return "backoffice", extra
    if u.prodejna_id in store_names:
        extra["prodejna_id"] = u.prodejna_id
        extra["prodejna_nazev"] = store_names[u.prodejna_id]
        return "prodejna", extra
    return "ostatni", extra


def _storeless_sort_key(item: dict) -> tuple:
    skupina = item.get("skupina")
    if skupina == "admini":
        return (0, "", item.get("jmeno_plne") or "")
    if skupina == "backoffice":
        return (1, "", item.get("jmeno_plne") or "")
    if skupina == "prodejna":
        return (2, item.get("prodejna_nazev") or "", item.get("jmeno_plne") or "")
    return (3, "", item.get("jmeno_plne") or "")


def assignees_for_store(store_id: int, user) -> list[dict]:
    role = getattr(user, "role", None)
    if role != "ADMIN":
        if store_id not in vedouci_store_ids(user):
            return []
    if not is_task_manager(user):
        return []

    excluded = get_excluded_report_user_ids()
    domovska = (
        WebUser.objects.filter(prodejna_id=store_id, aktivni=True)
        .exclude(id__in=excluded)
        .order_by("jmeno", "prijmeni")
    )
    brigadnici = (
        WebUser.objects.filter(role="BRIGADNIK", aktivni=True)
        .exclude(id__in=excluded)
        .order_by("jmeno", "prijmeni")
    )
    ostatni = (
        real_sales_staff_queryset()
        .exclude(prodejna_id=store_id)
        .exclude(role="BRIGADNIK")
        .order_by("jmeno", "prijmeni")
    )
    seen = set()
    result = []

    def _append_user(u: WebUser, skupina: str) -> None:
        if u.id in seen or is_excluded_task_assignee(u):
            return
        seen.add(u.id)
        display = _user_display(u, skupina)
        if display:
            result.append(display)

    for u in domovska:
        _append_user(u, "domaci")
    for u in brigadnici:
        _append_user(u, "brigadnik")
    for u in ostatni:
        _append_user(u, "ostatni")
    if role == "ADMIN":
        admini = WebUser.objects.filter(role="ADMIN", aktivni=True).order_by("jmeno", "prijmeni")
        for u in admini:
            _append_user(u, "admini")
    return result


def assignees_storeless(user) -> list[dict]:
    """Seznam uživatelů pro přiřazení úkolu bez pobočky (jen admin)."""
    if getattr(user, "role", None) != "ADMIN":
        return []

    from stores.models import Prodejna

    store_names = {
        p.id: (p.nazev_kratkiy or p.nazev or f"Prodejna #{p.id}").strip()
        for p in Prodejna.objects.filter(aktivni=True)
    }

    qs = WebUser.objects.filter(aktivni=True).order_by("jmeno", "prijmeni")
    result = []
    seen = set()
    for u in qs:
        if u.id in seen or is_excluded_task_assignee(u):
            continue
        if not _assignee_allowed_storeless(u):
            continue
        seen.add(u.id)
        skupina, extra = _storeless_skupina(u, store_names)
        display = _user_display(u, skupina)
        if display:
            display.update(extra)
            result.append(display)
    result.sort(key=_storeless_sort_key)
    return result
