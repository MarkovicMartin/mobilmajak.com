from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import Ukol
from .serializers import UkolSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def tasks_list_create(request):
    """Seznam úkolů a vytvoření nového úkolu.

    - Běžní uživatelé vidí jen své přiřazené úkoly.
    - Admin může vidět všechny úkoly a volitelně filtrovat podle `prodejce_id` a `stav`.
    """

    if request.method == "GET":
        stav = request.GET.get("stav", "vse")
        prodejce_id = request.GET.get("prodejce_id")

        # Admin vidí vše; ostatní jen své úkoly
        if getattr(request.user, "role", None) == "ADMIN":
            qs = Ukol.objects.all()
            if prodejce_id:
                qs = qs.filter(id_prodejce_ukol=prodejce_id)
        else:
            qs = Ukol.objects.filter(id_prodejce_ukol=request.user.id)

        if stav != "vse":
            qs = qs.filter(stav=stav)
        serializer = UkolSerializer(qs.order_by("-vytvoreno")[:200], many=True)
        return Response(serializer.data)

    # POST
    data = request.data.copy()
    data.setdefault("id_prodejce_ukol", request.user.id)
    data.setdefault("id_prodejce_zadal", request.user.id)
    serializer = UkolSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def task_detail(request, task_id: int):
    """Úprava stavu/obsahu nebo smazání úkolu (pouze vlastník nebo admin)."""
    try:
        task = Ukol.objects.get(id=task_id)
    except Ukol.DoesNotExist:
        return Response({"error": "Úkol nenalezen"}, status=status.HTTP_404_NOT_FOUND)

    # Oprávnění: admin nebo vlastník (přiřazený i zadavatel)
    if request.user.role != "ADMIN" and request.user.id not in (task.id_prodejce_ukol, task.id_prodejce_zadal):
        return Response({"error": "Nemáte oprávnění"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "DELETE":
        task.delete()
        return Response({"message": "Úkol smazán"})

    # PUT
    serializer = UkolSerializer(task, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


