"""Executa o ETL etapa por etapa (extração, transformação e carga) e mostra o resultado de cada uma.

Como rodar:
  - VS Code: abra este arquivo e clique em "Run Python File" (▶), ou use F5 e escolha uma configuração.
  - Terminal: python executar_etl.py            (com consulta de CEP, precisa de internet)
              python executar_etl.py --sem-api  (offline, só com o dicionário de bairros)
              python executar_etl.py --saida saida   (também exporta clientes e auditoria em CSV)
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from clientes.etl_service import carregar_no_banco, exportar_csv  # noqa: E402
from clientes.models import Auditoria, Cliente, Vendedor  # noqa: E402
from etl.cep_client import ClienteCep  # noqa: E402
from etl.normalizers import carregar_dicionario  # noqa: E402
from etl.pipeline import extrair, resumir, transformar  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="ETL da Distribuidora Vetor, etapa por etapa")
    ap.add_argument("--sem-api", action="store_true", help="não consulta ViaCEP/BrasilAPI")
    ap.add_argument("--saida", default=None, help="pasta para exportar clientes e auditoria em CSV")
    args = ap.parse_args(argv)

    print("=" * 60)
    print("1. EXTRAÇÃO")
    print("=" * 60)
    linhas = extrair(RAIZ / "data" / "clientes_distribuidora_vetor.csv")
    grafias = {(linha["bairro_informado"] or "").strip() for linha in linhas}
    print(f"{len(linhas)} registros lidos do CSV")
    print(f"{len(grafias)} grafias distintas de bairro (incluindo o campo vazio)")
    print("Exemplo, primeiro registro:", {k: linhas[0][k] for k in ("id_cliente", "bairro_informado", "cep")})

    print()
    print("=" * 60)
    print("2. TRANSFORMAÇÃO")
    print("=" * 60)
    cliente_cep = None if args.sem_api else ClienteCep(str(RAIZ / "cache" / "cep_cache.sqlite"))
    print("Consulta de CEP:", "desligada (--sem-api)" if args.sem_api else "ViaCEP, com BrasilAPI de reserva e cache local")
    registros, auditoria = transformar(linhas, carregar_dicionario(), cliente_cep)
    print(f"{len(registros)} clientes tratados, {len(auditoria)} linhas de auditoria")
    bairros = Counter(r["bairro"] or "(sem bairro)" for r in registros)
    print("Bairros após a normalização:", dict(bairros.most_common()))
    print("Status do CEP:", dict(Counter(r["cep_status"] for r in registros)))
    print("Origem do bairro:", dict(Counter(r["bairro_fonte"] for r in registros)))
    print("Exemplos de auditoria (valor original -> valor tratado):")
    for a in [a for a in auditoria if a["campo"] == "bairro"][:3]:
        print(f"  {a['id_cliente']}: {a['valor_original']!r} -> {a['valor_tratado']!r}  [{a['criterio']}]")

    print()
    print("=" * 60)
    print("3. CARGA")
    print("=" * 60)
    carregar_no_banco(registros, auditoria)
    banco = settings_banco()
    print(f"Banco: {banco}")
    print(f"{Cliente.objects.count()} clientes, {Vendedor.objects.count()} vendedores e "
          f"{Auditoria.objects.count()} linhas de auditoria gravados")
    if args.saida:
        exportar_csv(args.saida)
        print(f"CSV exportados em: {args.saida}")

    print()
    print("RESUMO")
    print(json.dumps(resumir(linhas, registros, auditoria, cliente_cep), ensure_ascii=False, indent=2, default=str))


def settings_banco():
    from django.conf import settings
    cfg = settings.DATABASES["default"]
    return f"PostgreSQL ({cfg['NAME']})" if "postgresql" in cfg["ENGINE"] else f"SQLite ({cfg['NAME']})"


if __name__ == "__main__":
    try:
        main()
    except UnicodeDecodeError as erro:
        from config.erros import tratar_erro_de_conexao

        tratar_erro_de_conexao(erro)
