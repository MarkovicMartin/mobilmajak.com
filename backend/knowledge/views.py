import os

from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import KnowledgeDocument
from .permissions import IsAdminRole
from .search import build_answer
from .serializers import KnowledgeDocumentSerializer


class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeDocumentSerializer
    queryset = KnowledgeDocument.objects.select_related('nahral')
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'download'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'role', None) != 'ADMIN':
            qs = qs.filter(aktivni=True)
        query = (self.request.query_params.get('q') or '').strip()
        if query:
            qs = qs.filter(Q(nazev__icontains=query) | Q(popis__icontains=query))
        return qs

    def perform_create(self, serializer):
        serializer.save(nahral=self.request.user)

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        document = self.get_object()
        if not document.soubor:
            raise Http404('Soubor chybí.')
        filename = document.original_filename or os.path.basename(document.soubor.name)
        try:
            handle = document.soubor.open('rb')
        except FileNotFoundError as exc:
            raise Http404('Soubor chybí.') from exc
        return FileResponse(handle, as_attachment=True, filename=filename)


class KnowledgeAskView(APIView):
    """POST {question} -> {answer, sources}. Tělo odpovědi může později dodat model."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        question = request.data.get('question', request.data.get('dotaz', ''))
        question = str(question or '').strip()
        if not question:
            return Response({'detail': 'Zadejte dotaz.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(question) > 500:
            return Response({'detail': 'Dotaz je příliš dlouhý.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(build_answer(question))
