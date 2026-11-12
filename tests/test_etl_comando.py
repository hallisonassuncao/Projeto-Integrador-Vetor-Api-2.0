import json
from io import StringIO

import pytest
from django.core.management import call_command

from clientes.models import Auditoria, Cliente, Vendedor
from etl.cep_client import ConsultaCep
from tests.conftest import CepFalso

pytestmark = pytest.mark.django_db


def rodar(*args):
    saida = StringIO()
    call_command("rodar_etl", *args, stdout=saida)
    return json.loads(saida.getvalue())


def test_etl_sem_api_carrega_clientes_vendedores_e_auditoria():
    resumo = rodar("--sem-api")
    assert resumo["clientes"] == 47 and resumo["vendedores"] == 5
    assert Cliente.objects.count() == 47 and Vendedor.objects.count() == 5
    assert Auditoria.objects.count() == resumo["linhas_de_auditoria"]
    bairros = set(Cliente.objects.exclude(bairro_normalizado=None)
                  .values_list("bairro_normalizado", flat=True))
    assert bairros == {"Águas Claras", "Taguatinga", "Vicente Pires", "Guará"}
    assert Cliente.objects.get(pk="CLI0047").bairro_normalizado is None


def test_etl_e_idempotente():
    rodar("--sem-api")
    primeira = Auditoria.objects.count()
    rodar("--sem-api")
    assert Cliente.objects.count() == 47 and Vendedor.objects.count() == 5
    assert Auditoria.objects.count() == primeira


def test_etl_preserva_cliente_criado_pela_api():
    vendedor = Vendedor.objects.create(nome_vendedor="Novo Vendedor")
    Cliente.objects.create(id_cliente="CLI9999", razao_social="Criado pela API", vendedor=vendedor)
    rodar("--sem-api")
    assert Cliente.objects.filter(pk="CLI9999").exists()
    assert Cliente.objects.count() == 48


def test_etl_com_cep_simulado_marca_divergencia(monkeypatch):
    falso = CepFalso({"72140-010": ConsultaCep("72140-010", "Taguatinga Sul", "Brasília", "DF", "viacep")})
    monkeypatch.setattr("clientes.management.commands.rodar_etl.ClienteCep", lambda caminho: falso)
    rodar()
    cli = Cliente.objects.get(pk="CLI0002")
    assert cli.divergencia_cep_bairro is True
    assert (cli.bairro_normalizado, cli.subdivisao) == ("Taguatinga", "Sul")
    assert falso.chamadas  # a API simulada foi consultada


def test_etl_exporta_csv_de_clientes_e_auditoria(tmp_path):
    import csv

    def ler(nome):
        with open(tmp_path / nome, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f, delimiter=";"))

    resumo = rodar("--sem-api", "--saida", str(tmp_path))
    assert len(ler("clientes_tratados.csv")) == 47
    auditoria = ler("auditoria_tratamento.csv")
    assert len(auditoria) == resumo["linhas_de_auditoria"]
    assert {"valor_original", "valor_tratado", "criterio", "fonte"} <= set(auditoria[0])


def test_consultas_sql_do_projeto_executam():
    """O arquivo consultas.sql roda sem erro e a primeira consulta agrupa os 4 bairros (+ sem bairro)."""
    from pathlib import Path

    import sqlparse
    from django.conf import settings
    from django.db import connection

    rodar("--sem-api")
    texto = (Path(settings.BASE_DIR) / "consultas.sql").read_text(encoding="utf-8")
    comandos = [c.strip().rstrip(";") for c in sqlparse.split(texto)
                if sqlparse.format(c, strip_comments=True).strip()]
    assert len(comandos) == 9
    with connection.cursor() as cursor:
        for i, comando in enumerate(comandos):
            cursor.execute(comando)
            linhas = cursor.fetchall()
            if i == 0:
                assert len(linhas) == 5 and linhas[0][1] == 22
