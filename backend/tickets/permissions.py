"""Oprávnění ke správě ticketů (mimo plné ADMIN)."""


def can_manage_tickets(user) -> bool:
    if not user or getattr(user, 'is_anonymous', True):
        return False
    if getattr(user, 'role', None) == 'ADMIN':
        return True
    moduly = getattr(user, 'moduly', None) or []
    return 'tickets_admin' in moduly
