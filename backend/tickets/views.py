from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Exists, OuterRef, Q, Subquery, F
from django.db.models.functions import Coalesce
from .models import Ticket, TicketImage, TicketComment, TicketUserReadState
from .serializers import TicketSerializer, TicketListSerializer, TicketCommentSerializer
from .webhooks import notify_ticket_created, notify_comment_added


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


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def tickets_list_create(request):
    if request.method == 'GET':
        if getattr(request.user, 'role', None) == 'ADMIN':
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

    is_admin = getattr(request.user, 'role', None) == 'ADMIN'
    is_owner = ticket.autor_id == request.user.id

    if not is_admin and not is_owner:
        return Response({'success': False, 'error': 'Nemáte oprávnění.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = TicketSerializer(ticket, context={'request': request})
        return Response({'success': True, 'ticket': serializer.data})

    if request.method == 'PATCH':
        if not is_admin:
            return Response({'success': False, 'error': 'Pouze admin může měnit stav.'}, status=status.HTTP_403_FORBIDDEN)
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
        serializer = TicketSerializer(ticket, context={'request': request})
        return Response({'success': True, 'ticket': serializer.data})

    if request.method == 'DELETE':
        if not is_admin:
            return Response({'success': False, 'error': 'Pouze admin může mazat tickety.'}, status=status.HTTP_403_FORBIDDEN)
        ticket.delete()
        return Response({'success': True, 'message': 'Ticket smazán.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ticket_add_comment(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return Response({'success': False, 'error': 'Ticket nenalezen.'}, status=status.HTTP_404_NOT_FOUND)

    is_admin = getattr(request.user, 'role', None) == 'ADMIN'
    is_owner = ticket.autor_id == request.user.id
    if not is_admin and not is_owner:
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

    is_admin = getattr(request.user, 'role', None) == 'ADMIN'
    is_owner = ticket.autor_id == request.user.id
    if not is_admin and not is_owner:
        return None, None, Response({'success': False, 'error': 'Nemáte oprávnění.'}, status=status.HTTP_403_FORBIDDEN)
    return ticket, comment, None


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def ticket_comment_modify(request, ticket_id, comment_id):
    ticket, comment, err = _ticket_comment_get(request, ticket_id, comment_id)
    if err:
        return err

    is_admin = getattr(request.user, 'role', None) == 'ADMIN'

    if request.method == 'DELETE':
        if not is_admin:
            return Response({'success': False, 'error': 'Mazat komentáře může pouze administrátor.'}, status=status.HTTP_403_FORBIDDEN)
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
    if getattr(request.user, 'role', None) == 'ADMIN':
        return Response({'success': True, 'unread_count': 0})
    uid = request.user.id
    return Response({
        'success': True,
        'unread_count': _unread_ticket_count_for_author(uid),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ticket_mark_read(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return Response({'success': False, 'error': 'Ticket nenalezen.'}, status=status.HTTP_404_NOT_FOUND)

    if ticket.autor_id != request.user.id:
        return Response({'success': False, 'error': 'Pouze autor tiketu může označit přečtení.'}, status=status.HTTP_403_FORBIDDEN)

    TicketUserReadState.objects.update_or_create(
        user_id=request.user.id,
        ticket=ticket,
        defaults={'last_seen_at': timezone.now()},
    )
    return Response({
        'success': True,
        'unread_count': _unread_ticket_count_for_author(request.user.id),
    })
