from stores.models import Prodejna


def build_user_list_serializer_context(users):
    """Prefetch mapy pro WebUserSerializer – eliminuje N+1 dotazy."""
    user_list = list(users)
    prodejna_ids = {u.prodejna_id for u in user_list if u.prodejna_id}
    prodejna_map = {}
    if prodejna_ids:
        prodejna_map = {p.id: p for p in Prodejna.objects.filter(id__in=prodejna_ids)}

    user_ids = [u.id for u in user_list]
    vedouci_store_by_user_id = {}
    if user_ids:
        for row in Prodejna.objects.filter(vedouci_user_id__in=user_ids).values('vedouci_user_id', 'id'):
            vedouci_store_by_user_id[row['vedouci_user_id']] = row['id']

    return {
        'prodejna_map': prodejna_map,
        'vedouci_store_by_user_id': vedouci_store_by_user_id,
    }
