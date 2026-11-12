import json

from django.conf import settings
from django.core.management.base import BaseCommand

from clientes.etl_service import executar_etl, exportar_csv
from etl.cep_client import ClienteCep


class Command(BaseCommand):
    help = "Executa o ETL: CSV -> normalização -> consulta de CEP -> banco (clientes, vendedores, auditoria)."

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=str(settings.BASE_DIR / "data" / "clientes_distribuidora_vetor.csv"))
        parser.add_argument("--cache", default=str(settings.BASE_DIR / "cache" / "cep_cache.sqlite"))
        parser.add_argument("--dicionario", default=None, help="CSV do dicionário de bairros (opcional)")
        parser.add_argument("--saida", default=None, help="pasta para exportar clientes e auditoria em CSV")
        parser.add_argument("--sem-api", action="store_true", help="não consulta ViaCEP/BrasilAPI")

    def handle(self, *args, **opcoes):
        cliente_cep = None if opcoes["sem_api"] else ClienteCep(opcoes["cache"])
        resumo = executar_etl(opcoes["csv"], cliente_cep, opcoes["dicionario"])
        if opcoes["saida"]:
            exportar_csv(opcoes["saida"])
        self.stdout.write(json.dumps(resumo, ensure_ascii=False, indent=2, default=str))
