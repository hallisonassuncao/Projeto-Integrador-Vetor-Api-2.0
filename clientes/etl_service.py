"""Orquestra o ETL: extrai o CSV, transforma (etl/) e carrega no banco via Django ORM."""
import csv
from pathlib import Path

from django.db import transaction

from etl.normalizers import carregar_dicionario
from etl.pipeline import extrair, resumir, transformar

from .models import Auditoria, Cliente, Vendedor

VENDEDOR_PADRAO = "(não informado)"


@transaction.atomic
def carregar_no_banco(registros, auditoria):
    """Idempotente: atualiza clientes pelo id_cliente e recria a auditoria deles."""
    nomes = {r["vendedor_responsavel"] or VENDEDOR_PADRAO for r in registros}
    vendedores = {n: Vendedor.objects.get_or_create(nome_vendedor=n)[0] for n in sorted(nomes)}

    for r in registros:
        Cliente.objects.update_or_create(
            id_cliente=r["id_cliente"],
            defaults={
                "razao_social": r["razao_social"],
                "cnpj_normalizado": r["cnpj"],
                "telefone_normalizado": r["telefone"],
                "email": r["email"],
                "bairro_normalizado": r["bairro"],
                "cep_normalizado": r["cep"],
                "data_cadastro_normalizado": r["data_cadastro"],
                "vendedor": vendedores[r["vendedor_responsavel"] or VENDEDOR_PADRAO],
                "cidade": r["cidade"], "uf": r["uf"],
                "bairro_informado": r["bairro_informado"], "subdivisao": r["subdivisao"],
                "bairro_fonte": r["bairro_fonte"], "cep_status": r["cep_status"],
                "telefone_tipo": r["telefone_tipo"], "cnpj_dv_valido": r["cnpj_dv_valido"],
                "email_valido": r["email_valido"],
                "divergencia_cep_bairro": r["divergencia_cep_bairro"],
                "revisao_manual": r["revisao_manual"], "data_ambigua": r["data_ambigua"],
            },
        )

    ids = [r["id_cliente"] for r in registros]
    Auditoria.objects.filter(cliente_id__in=ids).delete()
    Auditoria.objects.bulk_create([
        Auditoria(cliente_id=a["id_cliente"], campo=a["campo"], valor_original=a["valor_original"],
                  valor_tratado=a["valor_tratado"], criterio=a["criterio"], fonte=a["fonte"],
                  revisao_manual=a["revisao_manual"])
        for a in auditoria
    ])


def executar_etl(caminho_csv, cliente_cep=None, caminho_dicionario=None):
    linhas = extrair(caminho_csv)
    dicionario = carregar_dicionario(caminho_dicionario)
    registros, auditoria = transformar(linhas, dicionario, cliente_cep)
    carregar_no_banco(registros, auditoria)
    resumo = resumir(linhas, registros, auditoria, cliente_cep)
    resumo["vendedores"] = Vendedor.objects.count()
    return resumo


def _gravar_csv(caminho, linhas):
    linhas = list(linhas)
    if not linhas:
        return
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)


def exportar_csv(pasta):
    """Exporta a base tratada e a trilha de auditoria (valor original -> tratado -> critério/fonte)."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    _gravar_csv(pasta / "clientes_tratados.csv", Cliente.objects.order_by("id_cliente").values(
        "id_cliente", "razao_social", "cnpj_normalizado", "telefone_normalizado", "email",
        "bairro_informado", "bairro_normalizado", "subdivisao", "bairro_fonte", "cep_normalizado",
        "cep_status", "data_cadastro_normalizado", "vendedor__nome_vendedor",
        "divergencia_cep_bairro", "revisao_manual"))
    _gravar_csv(pasta / "auditoria_tratamento.csv", Auditoria.objects.values(
        "cliente_id", "campo", "valor_original", "valor_tratado", "criterio", "fonte",
        "revisao_manual", "executado_em"))
