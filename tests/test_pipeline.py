from pathlib import Path

from etl.cep_client import ConsultaCep
from etl.pipeline import extrair, resumir, transformar, tratar_cliente
from tests.conftest import CepFalso

CSV = Path(__file__).parent.parent / "data" / "clientes_distribuidora_vetor.csv"


def linha(**kw):
    base = {"id_cliente": "T1", "razao_social": "  Loja   Teste ", "cnpj": "11222333000181",
            "telefone": "61970855700", "email": "a@b.com", "bairro_informado": "aguas claras",
            "cep": "", "cidade": "Brasília", "uf": "DF", "data_cadastro": "2022-01-31",
            "vendedor_responsavel": "Fulano"}
    base.update(kw)
    return base


def test_tratar_cliente_sem_api(dicionario):
    reg, aud = tratar_cliente(linha(), dicionario)
    assert reg["razao_social"] == "Loja Teste"
    assert reg["bairro"] == "Águas Claras" and reg["bairro_fonte"] == "informado"
    assert reg["telefone"] == "+5561970855700" and reg["cnpj"] == "11.222.333/0001-81"
    campos = {a["campo"] for a in aud}
    assert {"razao_social", "telefone", "bairro", "cep"} <= campos
    bairro = next(a for a in aud if a["campo"] == "bairro")
    assert bairro["valor_original"] == "aguas claras" and bairro["valor_tratado"] == "Águas Claras"


def test_cep_divergente_prevalece_a_api_e_audita(dicionario):
    api = CepFalso({"72140-010": ConsultaCep("72140-010", "Taguatinga Sul", "Brasília", "DF", "viacep")})
    reg, aud = tratar_cliente(linha(bairro_informado="Sul (Águas Claras)", cep="72140-010"), dicionario, api)
    assert (reg["bairro"], reg["subdivisao"]) == ("Taguatinga", "Sul")
    assert reg["divergencia_cep_bairro"] is True
    b = next(a for a in aud if a["campo"] == "bairro")
    assert b["fonte"] == "api_cep" and "divergencia_api_prevalece" in b["criterio"]
    assert "viacep" in b["criterio"]


def test_cep_invalido_nao_chama_api(dicionario):
    api = CepFalso({})
    reg, _ = tratar_cliente(linha(cep="00000-000"), dicionario, api)
    assert api.chamadas == [] and reg["cep_status"] == "invalido" and reg["cep"] is None


def test_cep_de_outra_uf_e_ignorado(dicionario):
    api = CepFalso({"01001-000": ConsultaCep("01001-000", "Sé", "São Paulo", "SP", "viacep")})
    reg, aud = tratar_cliente(linha(cep="01001-000"), dicionario, api)
    assert reg["bairro"] == "Águas Claras" and reg["bairro_fonte"] == "informado"
    assert any(a["criterio"] == "cep_de_outra_uf_ignorado" and a["revisao_manual"] for a in aud)


def test_transformacao_do_csv_real(dicionario):
    api = CepFalso({"72140-010": ConsultaCep("72140-010", "Taguatinga Sul", "Brasília", "DF", "viacep")})
    linhas = extrair(CSV)
    clientes, auditoria = transformar(linhas, dicionario, api)
    r = resumir(linhas, clientes, auditoria, api)
    assert r["clientes"] == 47
    assert r["bairros_distintos_depois"] == 4
    assert r["grafias_distintas_bairro_antes"] == 26   # 25 grafias + vazio
    assert r["clientes_sem_bairro"] == 1               # CLI0047
    assert r["divergencias_cep_bairro"] == 1           # CLI0002
    assert r["cnpj_dv_invalido"] == 47                 # base sintética: sinalizados, nunca descartados


def test_valores_cabem_nos_tamanhos_das_colunas(dicionario):
    """SQLite não impõe max_length; o PostgreSQL impõe. Confere os limites dos modelos."""
    from django.db import models as m

    from clientes.models import Auditoria, Cliente

    api = CepFalso({"72140-010": ConsultaCep("72140-010", "Sul (Águas Claras)", "Brasília", "DF", "viacep")})
    clientes, auditoria = transformar(extrair(CSV), dicionario, api)

    mapa_cliente = {"cnpj": "cnpj_normalizado", "telefone": "telefone_normalizado",
                    "bairro": "bairro_normalizado", "cep": "cep_normalizado"}
    for registro in clientes:
        for chave, valor in registro.items():
            nome = mapa_cliente.get(chave, chave)
            if valor is None or not hasattr(Cliente, nome) or not isinstance(valor, str):
                continue
            campo = Cliente._meta.get_field(nome)
            if isinstance(campo, m.CharField) and campo.max_length:
                assert len(valor) <= campo.max_length, f"Cliente.{nome}: {len(valor)} > {campo.max_length}"
    for a in auditoria:
        for nome in ("campo", "fonte"):
            assert len(a[nome]) <= Auditoria._meta.get_field(nome).max_length


class CepComFalha(CepFalso):
    def consultar(self, cep):
        self.chamadas.append(cep)
        self.ultimo_status = "falha_na_consulta"
        return None


def test_cep_inexistente_na_api_e_registrado_na_auditoria(dicionario):
    api = CepFalso({})  # a API "não conhece" o CEP
    reg, aud = tratar_cliente(linha(bairro_informado="Vte Pires", cep="72110-800"), dicionario, api)
    assert reg["bairro"] == "Vicente Pires" and reg["bairro_fonte"] == "informado"
    cep = next(a for a in aud if a["campo"] == "cep")
    assert cep["criterio"] == "cep_nao_encontrado_na_api" and cep["fonte"] == "api_cep"
    bairro = next(a for a in aud if a["campo"] == "bairro")
    assert "cep_nao_encontrado_na_api" in bairro["criterio"]


def test_falha_de_consulta_nao_e_confundida_com_cep_inexistente(dicionario):
    _, aud = tratar_cliente(linha(cep="72110-800"), dicionario, CepComFalha({}))
    assert [a["criterio"] for a in aud if a["campo"] == "cep"] == ["cep_consulta_falhou"]


def test_resumo_conta_ceps_nao_encontrados(dicionario):
    api = CepFalso({})
    linhas = [linha(id_cliente="A", cep="72110-800"), linha(id_cliente="B", cep="")]
    clientes, auditoria = transformar(linhas, dicionario, api)
    assert resumir(linhas, clientes, auditoria, api)["ceps_nao_encontrados"] == 1
