from django.contrib import admin
from django.db.models import Count

from .models import Auditoria, Cliente, Vendedor


class AuditoriaInline(admin.TabularInline):
    model = Auditoria
    extra = 0
    can_delete = False
    fields = ("campo", "valor_original", "valor_tratado", "criterio", "fonte", "revisao_manual")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ("id_vendedor", "nome_vendedor", "total_clientes")
    search_fields = ("nome_vendedor",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_total=Count("clientes"))

    @admin.display(description="Clientes", ordering="_total")
    def total_clientes(self, obj):
        return obj._total


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("id_cliente", "razao_social", "bairro_normalizado", "cep_normalizado",
                    "vendedor", "revisao_manual", "divergencia_cep_bairro")
    list_filter = ("bairro_normalizado", "vendedor", "revisao_manual", "divergencia_cep_bairro")
    search_fields = ("id_cliente", "razao_social", "cnpj_normalizado")
    list_select_related = ("vendedor",)
    inlines = [AuditoriaInline]


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ("cliente", "campo", "valor_original", "valor_tratado", "criterio", "fonte", "revisao_manual")
    list_filter = ("campo", "fonte", "revisao_manual")
    search_fields = ("cliente__id_cliente", "valor_original", "valor_tratado")
    list_select_related = ("cliente",)
