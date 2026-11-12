from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Cliente, Vendedor
from .serializers import BairroResumoSerializer, ClienteSerializer, VendedorSerializer


def _responder_clientes(view, queryset):
    """Lista paginada de clientes (usada pelas rotas de relacionamento)."""
    pagina = view.paginate_queryset(queryset)
    dados = ClienteSerializer(pagina, many=True, context={"request": view.request}).data
    return view.get_paginated_response(dados)


@extend_schema_view(
    list=extend_schema(summary="Listar clientes"),
    retrieve=extend_schema(summary="Detalhar cliente"),
    create=extend_schema(summary="Criar cliente (autenticado)"),
    update=extend_schema(summary="Substituir cliente (autenticado)"),
    partial_update=extend_schema(summary="Editar cliente (autenticado)"),
    destroy=extend_schema(summary="Excluir cliente (autenticado)"),
)
class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.select_related("vendedor").all()
    serializer_class = ClienteSerializer

    @extend_schema(summary="Resumo: total de clientes por bairro normalizado",
                   responses=BairroResumoSerializer(many=True))
    @action(detail=False, methods=["get"], url_path="bairros", pagination_class=None)
    def bairros(self, request):
        resumo = (Cliente.objects.exclude(bairro_normalizado__isnull=True)
                  .values("bairro_normalizado").annotate(total=Count("id_cliente"))
                  .order_by("-total", "bairro_normalizado"))
        return Response(list(resumo))

    @extend_schema(
        summary="Listar clientes de um bairro",
        parameters=[OpenApiParameter("nome", str, OpenApiParameter.PATH,
                                     description="Bairro normalizado. Aceita variações de grafia (ex.: 'aguas claras').")],
        responses=ClienteSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path=r"bairro/(?P<nome>[^/]+)")
    def por_bairro(self, request, nome):
        canonico = services.bairro_canonico(nome)
        filtro = ({"bairro_normalizado": canonico} if canonico
                  else {"bairro_normalizado__iexact": nome.strip()})
        return _responder_clientes(self, self.get_queryset().filter(**filtro))

    @extend_schema(
        summary="Listar clientes de um vendedor",
        parameters=[OpenApiParameter("vendedor_id", int, OpenApiParameter.PATH, description="id_vendedor")],
        responses=ClienteSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path=r"vendedor/(?P<vendedor_id>\d+)")
    def por_vendedor(self, request, vendedor_id):
        vendedor = get_object_or_404(Vendedor, pk=vendedor_id)
        return _responder_clientes(self, self.get_queryset().filter(vendedor=vendedor))


@extend_schema_view(
    list=extend_schema(summary="Listar vendedores"),
    retrieve=extend_schema(summary="Detalhar vendedor"),
    create=extend_schema(summary="Criar vendedor (autenticado)"),
    update=extend_schema(summary="Substituir vendedor (autenticado)"),
    partial_update=extend_schema(summary="Editar vendedor (autenticado)"),
    destroy=extend_schema(summary="Excluir vendedor (autenticado; 409 se tiver clientes)"),
)
class VendedorViewSet(viewsets.ModelViewSet):
    queryset = Vendedor.objects.all()
    serializer_class = VendedorSerializer

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Vendedor possui clientes vinculados e não pode ser excluído."},
                status=status.HTTP_409_CONFLICT,
            )

    @extend_schema(summary="Listar clientes de um vendedor", responses=ClienteSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="clientes")
    def clientes(self, request, pk=None):
        vendedor = self.get_object()
        return _responder_clientes(self, vendedor.clientes.select_related("vendedor"))
