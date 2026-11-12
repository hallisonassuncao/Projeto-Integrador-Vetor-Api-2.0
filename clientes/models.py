from django.db import models
from django.utils import timezone


class Vendedor(models.Model):
    id_vendedor = models.AutoField(primary_key=True)
    nome_vendedor = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nome_vendedor"]
        verbose_name = "vendedor"
        verbose_name_plural = "vendedores"

    def __str__(self):
        return self.nome_vendedor


class Cliente(models.Model):
    id_cliente = models.CharField(max_length=20, primary_key=True)
    razao_social = models.CharField(max_length=200)
    cnpj_normalizado = models.CharField(max_length=18, null=True, blank=True)
    telefone_normalizado = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(max_length=150, null=True, blank=True)
    bairro_normalizado = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    cep_normalizado = models.CharField(max_length=9, null=True, blank=True)
    data_cadastro_normalizado = models.DateField(null=True, blank=True)
    # Proteção: um vendedor com clientes não pode ser excluído (a API responde 409).
    vendedor = models.ForeignKey(Vendedor, on_delete=models.PROTECT, related_name="clientes")

    # Metadados do ETL (visíveis no admin; não expostos na API)
    cidade = models.CharField(max_length=80, null=True, blank=True)
    uf = models.CharField(max_length=2, null=True, blank=True)
    bairro_informado = models.CharField(max_length=100, null=True, blank=True)
    subdivisao = models.CharField(max_length=30, null=True, blank=True)
    bairro_fonte = models.CharField(max_length=30, null=True, blank=True)
    cep_status = models.CharField(max_length=30, null=True, blank=True)
    telefone_tipo = models.CharField(max_length=10, null=True, blank=True)
    cnpj_dv_valido = models.BooleanField(null=True, blank=True)
    email_valido = models.BooleanField(null=True, blank=True)
    divergencia_cep_bairro = models.BooleanField(default=False)
    revisao_manual = models.BooleanField(default=False)
    data_ambigua = models.BooleanField(default=False)

    class Meta:
        ordering = ["id_cliente"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return f"{self.id_cliente} - {self.razao_social}"

    @classmethod
    def proximo_id(cls) -> str:
        """Próximo código no padrão CLI0001 (usado quando a API cria um cliente sem id)."""
        numeros = [int(i[3:]) for i in cls.objects.filter(id_cliente__startswith="CLI")
                   .values_list("id_cliente", flat=True) if i[3:].isdigit()]
        return f"CLI{(max(numeros) + 1 if numeros else 1):04d}"


class Auditoria(models.Model):
    """Trilha do ETL: valor original -> valor tratado -> critério/fonte. Só aparece no admin."""

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="auditorias")
    campo = models.CharField(max_length=30)
    valor_original = models.TextField(null=True, blank=True)
    valor_tratado = models.TextField(null=True, blank=True)
    criterio = models.TextField()
    fonte = models.CharField(max_length=30)
    revisao_manual = models.BooleanField(default=False)
    executado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["cliente_id", "id"]
        verbose_name = "auditoria"
        verbose_name_plural = "auditorias"

    def __str__(self):
        return f"{self.cliente_id} · {self.campo}"
