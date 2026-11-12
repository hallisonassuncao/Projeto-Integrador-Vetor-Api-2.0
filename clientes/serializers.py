from rest_framework import serializers

from . import services
from .models import Cliente, Vendedor


class VendedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendedor
        fields = ["id_vendedor", "nome_vendedor"]
        read_only_fields = ["id_vendedor"]


class ClienteSerializer(serializers.ModelSerializer):
    id_cliente = serializers.CharField(
        max_length=20, required=False,
        help_text="Opcional na criação: se omitido, é gerado no padrão CLI0001. Não pode ser alterado depois.",
    )
    vendedor_id = serializers.PrimaryKeyRelatedField(source="vendedor", queryset=Vendedor.objects.all())

    class Meta:
        model = Cliente
        fields = [
            "id_cliente", "razao_social", "cnpj_normalizado", "telefone_normalizado", "email",
            "bairro_normalizado", "cep_normalizado", "data_cadastro_normalizado", "vendedor_id",
        ]

    def validate_id_cliente(self, valor):
        if self.instance is None and Cliente.objects.filter(pk=valor).exists():
            raise serializers.ValidationError("Já existe um cliente com este id_cliente.")
        if self.instance is not None and valor != self.instance.pk:
            raise serializers.ValidationError("O id_cliente não pode ser alterado.")
        return valor

    def _normalizar(self, funcao, valor):
        try:
            return funcao(valor)
        except ValueError as erro:
            raise serializers.ValidationError(str(erro))

    def validate_cnpj_normalizado(self, valor):
        return self._normalizar(services.normalizar_cnpj_entrada, valor)

    def validate_telefone_normalizado(self, valor):
        return self._normalizar(services.normalizar_telefone_entrada, valor)

    def validate_cep_normalizado(self, valor):
        return self._normalizar(services.normalizar_cep_entrada, valor)

    def validate_bairro_normalizado(self, valor):
        return services.normalizar_bairro_entrada(valor)

    def create(self, validated_data):
        if not validated_data.get("id_cliente"):
            validated_data["id_cliente"] = Cliente.proximo_id()
        return super().create(validated_data)


class BairroResumoSerializer(serializers.Serializer):
    bairro_normalizado = serializers.CharField()
    total = serializers.IntegerField()
