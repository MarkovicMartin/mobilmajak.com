from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Exists, OuterRef, Q, Subquery, F
from django.db.models.functions import Coalesce
from datetime import timedelta
import hashlib
from .models import Ticket, TicketImage, TicketComment, TicketUserReadState
from .serializers import TicketSerializer, TicketListSerializer, TicketCommentSerializer
from .webhooks import notify_ticket_created, notify_comment_added
from .permissions import can_manage_tickets


def _unread_ticket_count_for_author(user_id):
    """Počet tiketů uživatele jako autora, u kterých je nová aktivita od posledního přečtení."""
    read_sq = TicketUserReadState.objects.filter(
        ticket_id=OuterRef('pk'),
        user_id=user_id,
    ).values('last_seen_at')[:1]

    qs = Ticket.objects.filter(autor_id=user_id).annotate(
        baseline=Coalesce(Subquery(read_sq), F('vytvoreno')),
    )

    unread_comment = Exists(
        TicketComment.objects.filter(
            ticket_id=OuterRef('pk'),
            vytvoreno__gt=OuterRef('baseline'),
        ).exclude(autor_id=OuterRef('autor_id'))
    )

    return qs.filter(Q(upraveno__gt=F('baseline')) | unread_comment).count()


def _unread_ticket_count_for_manager(user_id):
    """Počet otevřených ticketů s aktivitou od posledního přečtení (opravené nepočítáme)."""
    read_sq = TicketUserReadState.objects.filter(
        ticket_id=OuterRef('pk'),
        user_id=user_id,
    ).values('last_seen_at')[:1]

    qs = (
        Ticket.objects.exclude(stav='opraveno')
        .annotate(baseline=Coalesce(Subquery(read_sq), F('vytvoreno')))
    )

    unread_comment = Exists(
        TicketComment.objects.filter(
            ticket_id=OuterRef('pk'),
            vytvoreno__gt=OuterRef('baseline'),
        )
    )

    return qs.filter(Q(upraveno__gt=F('baseline')) | unread_comment).count()


UX_FRICTION_LABELS = {
    'rage_click': 'Rozzlobené opakované klikání',
    'dead_click': 'Klik na neinteraktivní prvek',
    'api_error': 'Chyba API',
    'js_error': 'Chyba JavaScriptu',
    'slow_action': 'Pomalá odezva aplikace',
}

UX_FRICTION_DEDUP_HOURS = 6


def _ux_fingerprint(user_id, kind, route, element, detail):
    raw = f'{user_id}|{kind}|{route}|{element}|{detail}'[:500]
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ux_friction_report(request):
    """Automatické hlášení UX záseků → ticket (s deduplikací)."""
    kind = (request.data.get('kind') or '').strip()
    if kind not in UX_FRICTION_LABELS:
        return Response(
            {'success': False, 'error': 'Neplatný typ události.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    route = (request.data.get('route') or '').strip()[:200]
    screen = (request.data.get('screen') or '').strip()[:100]
    element = (request.data.get('element') or '').strip()[:300]
    detail = (request.data.get('detail') or '').strip()[:1000]
    url = (request.data.get('url') or '').strip()[:500]

    fingerprint = _ux_fingerprint(request.user.id, kind, route, element, detail)
    since = timezone.now() - timedelta(hours=UX_FRICTION_DEDUP_HOURS)
    if Ticket.objects.filter(popis__contains=f'fp:{fingerprint}', vytvoreno__gte=since).exists():
        return Response({'success': True, 'skipped': True, 'reason': 'duplicate'})

    screen_label = screen or route or 'neznámá obrazovka'
    nazev = f'[UX] {UX_FRICTION_LABELS[kind]} – {screen_label}'[:200]
    popis_lines = [
        f'fp:{fingerprint}',
        f'Typ: {UX_FRICTION_LABELS[kind]} ({kind})',
        f'Obrazovka: {screen_label}',
        f'Cesta: {route or "—"}',
    ]
    if element:
        popis_lines.append(f'Prvek: {element}')
    if detail:
        popis_lines.append(f'Detail: {detail}')
    popis_lines.append('')
    popis_lines.append('Automaticky vytvořeno z chování v aplikaci (UX monitor).')

    jmeno = f"{getattr(request.user, 'jmeno', '')} {getattr(request.user, 'prijmeni', '')}".strip()
    ticket = Ticket.objects.create(
        nazev=nazev,
        popis='\n'.join(popis_lines),
        url=url,
        autor_id=request.user.id,
        autor_jmeno=jmeno or str(request.user.id),
    )
    notify_ticket_created(ticket)

    TicketUserReadState.objects.update_or_create(
        user_id=request.user.id,
        ticket=ticket,
        defaults={'last_seen_at': timezone.now()},
    )

    return Response({'success': True, 'ticket_id': ticket.id}, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def tickets_list_create(request):
    if request.method == 'GET':
        if can_manage_tickets(request.user):
            qs = Ticket.objects.all()
        else:
            qs = Ticket.objects.filter(autor_id=request.user.id)
        serializer = TicketListSerializer(qs, many=True, context={'request': request})
        return Response({'success': True, 'tickets': serializer.data})

    # POST — vytvoření nového ticketu
    nazev = request.data.get('nazev', '').strip()
    popis = request.data.get('popis', '').strip()
    if not nazev or not popis:
        return Response({'success': False, 'error': 'Název a popis jsou povinné.'}, status=status.HTTP_400_BAD_REQUEST)

    url = request.data.get('url', '').strip()[:500]
    jmeno = f"{getattr(request.user, 'jmeno', '')} {getattr(request.user, 'prijmeni', '')}".strip()
    ticket = Ticket.objects.create(
        nazev=nazev,
        popis=popis,
        url=url,
        autor_id=request.user.id,
        autor_jmeno=jmeno or str(request.user.id),
    )

    images = request.FILES.getlist('images')
    for img in images:
        TicketImage.objects.create(ticket=ticket, obrazek=img)

    notify_ticket_created(ticket)

    TicketUserReadState.objects.update_or_create(
        user_id=request.user.id,
        ticket=ticket,
        defaults={'last_seen_at': timezone.now()},
    )

    serializer = TicketSerializer(ticket, context={'request': request})
    return Response({'success': True, 'ticket': serializer.data}, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def ticket_detail(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return Response({'success': False, 'error': 'Ticket nenalezen.'}, status=status.HTTP_404_NOT_FOUND)

    is_manager = can_manage_tickets(request.user)
    is_owner = ticket.autor_id == request.user.id

    if not is_manager and not is_owner:
        return Response({'success': False, 'error': 'Nemáte oprávnění.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = TicketSerializer(ticket, context={'request': request})
        return Response({'success': True, 'ticket': serializer.data})

    if request.method == 'PATCH':
        if not is_manager:
            return Response({'success': False, 'error': 'Pouze správce ticketů může měnit stav.'}, status=status.HTTP_403_FORBIDDEN)
        stav = request.data.get('stav')
        valid_stavy = [s[0] for s in Ticket.STAVY]
        if stav not in valid_stavy:
            return Response({'success': False, 'error': f'Neplatný stav. Možnosti: {valid_stavy}'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.stav = stav
        if stav == 'opraveno' and not ticket.opraveno_at:
            ticket.opraveno_at = timezone.now()
        elif stav != 'opraveno':
            ticket.opraveno_at = None
        ticket.save(update_fields=['stav', 'opraveno_at', 'upraveno'])
        TicketUserReadState.objects.update_or_create(
            user_id=request.user.id,
            ticket=ticket,
            defaults={'last_seen_at': timezone.now()},
        )
        serializer = TicketSerializer(ticket, context={'request': request})
        return Response({'success': True, 'ticket': serializer.data})

    if request.method == 'DELETE':
        if not is_manager:
            return Response({'success': False, 'error': 'Pouze správce ticketů může mazat tickety.'}, status=status.HTTP_403_FORBIDDEN)
        ticket.delete()
        return Response({'success': True, 'message': 'Ticket smazán.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ticket_add_comment(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return Response({'success': False, 'error': 'Ticket nenalezen.'}, status=status.HTTP_404_NOT_FOUND)

    is_manager = can_manage_tickets(request.user)
    is_owner = ticket.autor_id == request.user.id
    if not is_manager and not is_owner:
        return Response({'success': False, 'error': 'Nemáte oprávnění.'}, status=status.HTTP_403_FORBIDDEN)

    text = request.data.get('text', '').strip()
    if not text:
        return Response({'success': False, 'error': 'Text komentáře je povinný.'}, status=status.HTTP_400_BAD_REQUEST)

    jmeno = f"{getattr(request.user, 'jmeno', '')} {getattr(request.user, 'prijmeni', '')}".strip()
    comment = TicketComment.objects.create(
        ticket=ticket,
        autor_id=request.user.id,
        autor_jmeno=jmeno or str(request.user.id),
        text=text,
    )
    notify_comment_added(ticket, comment)
    serializer = TicketCommentSerializer(comment)
    return Response({'success': True, 'comment': serializer.data}, status=status.HTTP_201_CREATED)


def _ticket_comment_get(request, ticket_id, comment_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return None, None, Response({'success': False, 'error': 'Ticket nenalezen.'}, status=status.HTTP_404_NOT_FOUND)
    try:
        comment = TicketComment.objects.get(id=comment_id, ticket_id=ticket.id)
    except TicketComment.DoesNotExist:
        return None, None, Response({'success': False, 'error': 'Komentář nenalezen.'}, status=status.HTTP_404_NOT_FOUND)

    is_manager = can_manage_tickets(request.user)
    is_owner = ticket.autor_id == request.user.id
    if not is_manager and not is_owner:
        return None, None, Response({'success': False, 'error': 'Nemáte oprávnění.'}, status=status.HTTP_403_FORBIDDEN)
    return ticket, comment, None


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def ticket_comment_modify(request, ticket_id, comment_id):
    ticket, comment, err = _ticket_comment_get(request, ticket_id, comment_id)
    if err:
        return err

    is_manager = can_manage_tickets(request.user)

    if request.method == 'DELETE':
        if not is_manager:
            return Response({'success': False, 'error': 'Mazat komentáře může pouze správce ticketů.'}, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response({'success': True, 'message': 'Komentář smazán.'})

    # PATCH – pouze vlastní komentář
    if comment.autor_id != request.user.id:
        return Response({'success': False, 'error': 'Upravit můžete jen vlastní komentář.'}, status=status.HTTP_403_FORBIDDEN)

    text = request.data.get('text', '').strip()
    if not text:
        return Response({'success': False, 'error': 'Text komentáře je povinný.'}, status=status.HTTP_400_BAD_REQUEST)

    comment.text = text
    comment.upraveno = timezone.now()
    comment.save(update_fields=['text', 'upraveno'])
    serializer = TicketCommentSerializer(comment)
    return Response({'success': True, 'comment': serializer.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tickets_unread_summary(request):
    uid = request.user.id
    if can_manage_tickets(request.user):
        count = _unread_ticket_count_for_manager(uid)
        role = 'manager'
    else:
        count = _unread_ticket_count_for_author(uid)
        role = 'author'
    return Response({
        'success': True,
        'unread_count': count,
        'role': role,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def tickets_mark_all_read(request):
    """Správce: označí všechny tickety jako přečtené (např. po otevření přehledu)."""
    if not can_manage_tickets(request.user):
        return Response({'success': False, 'error': 'Nemáte oprávnění.'}, status=status.HTTP_403_FORBIDDEN)

    now = timezone.now()
    for ticket in Ticket.objects.all().only('id'):
        TicketUserReadState.objects.update_or_create(
            user_id=request.user.id,
            ticket_id=ticket.id,
            defaults={'last_seen_at': now},
        )

    return Response({
        'success': True,
        'unread_count': _unread_ticket_count_for_manager(request.user.id),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ticket_mark_read(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return Response({'success': False, 'error': 'Ticket nenalezen.'}, status=status.HTTP_404_NOT_FOUND)

    is_manager = can_manage_tickets(request.user)
    if ticket.autor_id != request.user.id and not is_manager:
        return Response({'success': False, 'error': 'Nemáte oprávnění.'}, status=status.HTTP_403_FORBIDDEN)

    TicketUserReadState.objects.update_or_create(
        user_id=request.user.id,
        ticket=ticket,
        defaults={'last_seen_at': timezone.now()},
    )
    if is_manager:
        unread = _unread_ticket_count_for_manager(request.user.id)
    else:
        unread = _unread_ticket_count_for_author(request.user.id)
    return Response({
        'success': True,
        'unread_count': unread,
    })
