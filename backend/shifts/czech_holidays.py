"""České státní svátky – sdílené mezi views, payroll a dovolenou."""


def get_ceske_svatky(rok):
    """Vrací seznam českých státních svátků pro daný rok."""
    svatky = [
        (rok, 1, 1),
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
    if rok == 2025:
        svatky.extend([(2025, 4, 18), (2025, 4, 21)])
    elif rok == 2026:
        svatky.extend([(2026, 4, 3), (2026, 4, 6)])
    return svatky


def get_nazev_svatku(mesic, den):
    """Vrací název českého státního svátku podle data."""
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
        (4, 18): "Velký pátek",
        (4, 21): "Velikonoční pondělí",
        (4, 3): "Velký pátek",
        (4, 6): "Velikonoční pondělí",
    }
    return svatky_nazvy.get((mesic, den), "Státní svátek")
