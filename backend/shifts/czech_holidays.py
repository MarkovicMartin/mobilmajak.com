"""České státní svátky – sdílené mezi views, payroll a dovolenou."""
from datetime import timedelta

from shifts.mall_closure import easter_sunday


def get_ceske_svatky(rok):
    """Vrací seznam českých státních svátků pro daný rok."""
    nedela = easter_sunday(rok)
    patek = nedela - timedelta(days=2)
    pondeli = nedela + timedelta(days=1)
    svatky = [
        (rok, 1, 1),
        (rok, patek.month, patek.day),
        (rok, pondeli.month, pondeli.day),
        (rok, 5, 1),
        (rok, 5, 8),
        (rok, 7, 5),
        (rok, 7, 6),
        (rok, 9, 28),
        (rok, 10, 28),
        (rok, 11, 17),
        (rok, 12, 24),
        (rok, 12, 25),
        (rok, 12, 26),
    ]
    return svatky


def get_nazev_svatku(mesic, den, rok=None):
    """Vrací název českého státního svátku podle data."""
    if rok:
        nedela = easter_sunday(rok)
        patek = nedela - timedelta(days=2)
        pondeli = nedela + timedelta(days=1)
        if (mesic, den) == (patek.month, patek.day):
            return "Velký pátek"
        if (mesic, den) == (pondeli.month, pondeli.day):
            return "Velikonoční pondělí"
    svatky_nazvy = {
        (1, 1): "Nový rok",
        (5, 1): "Svátek práce",
        (5, 8): "Den vítězství",
        (7, 5): "Cyril a Metoděj",
        (7, 6): "Jan Hus",
        (9, 28): "Den české státnosti",
        (10, 28): "Vznik samostatného československého státu",
        (11, 17): "Den boje za svobodu a demokracii",
        (12, 24): "Štědrý den",
        (12, 25): "1. svátek vánoční",
        (12, 26): "2. svátek vánoční",
    }
    return svatky_nazvy.get((mesic, den), "Státní svátek")
