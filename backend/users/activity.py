"""Globální activity heartbeat – mapování modulů a exclude pravidla."""
from __future__ import annotations

MODULE_PREFIXES = (
    ('/api/finance/', 'finance'),
    ('/api/shifts/', 'shifts'),
    ('/api/analytics/', 'analytics'),
    ('/api/tasks/', 'tasks'),
    ('/api/plans/', 'plans'),
    ('/api/coaching/', 'coaching'),
    ('/api/orders/', 'orders'),
    ('/api/tickets/', 'tickets'),
    ('/api/packeta/', 'packeta'),
    ('/api/stores/', 'stores'),
    ('/api/news/', 'news'),
    ('/api/reklamace/', 'reklamace'),
    ('/api/wreck-parts/', 'wreck_parts'),
    ('/api/daily-duties/', 'daily_duties'),
    ('/api/users/', 'users'),
)

# Přesné cesty / prefixy, které se nelogují (poll, health, csrf, kamery).
EXCLUDE_EXACT = frozenset({
    '/health/',
    '/health',
    '/api/csrf/',
    '/api/csrf',
    '/api/users/csrf/',
    '/api/users/csrf',
    '/api/users/current/',
    '/api/users/current',
})

EXCLUDE_CONTAINS = (
    '/camera-events/',
    '/poll',
    '/stream',
)


def normalize_path(path: str) -> str:
    raw = (path or '').split('?', 1)[0].strip() or '/'
    if len(raw) > 200:
        return raw[:200]
    return raw


def module_from_path(path: str) -> str:
    p = normalize_path(path)
    for prefix, module in MODULE_PREFIXES:
        if p.startswith(prefix) or p == prefix.rstrip('/'):
            return module
    if p.startswith('/api/'):
        return 'other'
    return ''


def should_skip_path(path: str) -> bool:
    p = normalize_path(path)
    if not p.startswith('/api/') and p not in ('/health/', '/health'):
        return True
    if p in EXCLUDE_EXACT:
        return True
    lower = p.lower()
    return any(token in lower for token in EXCLUDE_CONTAINS)


def client_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()[:64]
    return (request.META.get('REMOTE_ADDR') or '')[:64]
