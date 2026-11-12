import pytest
from etl.normalizers import carregar_dicionario


@pytest.fixture(scope="session")
def dicionario():
    return carregar_dicionario()


class RespostaFalsa:
    def __init__(self, status=200, corpo=None, erro_json=False):
        self.status_code = status
        self._corpo = corpo
        self._erro_json = erro_json

    def json(self):
        if self._erro_json:
            raise ValueError("json inválido")
        return self._corpo


class SessaoFalsa:
    """Simula requests.Session: mapeia fragmento de URL -> resposta ou exceção. Nunca usa rede."""

    def __init__(self, respostas):
        self.respostas = respostas
        self.chamadas = []

    def get(self, url, timeout=None):
        self.chamadas.append(url)
        for trecho, resp in self.respostas.items():
            if trecho in url:
                if isinstance(resp, Exception):
                    raise resp
                return resp
        raise AssertionError(f"chamada inesperada: {url}")


# ------------------------------------------------------------------ Django / API
from django.contrib.auth import get_user_model  # noqa: E402
from rest_framework.authtoken.models import Token  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from clientes.models import Cliente, Vendedor  # noqa: E402


class CepFalso:
    """Substitui o ClienteCep: respostas fixas, sem rede e sem cache em disco."""

    def __init__(self, tabela):
        self.tabela = tabela
        self.chamadas = []
        self.stats = {"cache": 0, "api": 0, "falhas": 0}

    def consultar(self, cep):
        self.chamadas.append(cep)
        self.stats["api"] += 1
        resultado = self.tabela.get(cep)
        self.ultimo_status = "encontrado" if resultado else "nao_encontrado"
        return resultado


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def api_auth(db):
    usuario = get_user_model().objects.create_user("tester", password="senha-forte-123")
    token = Token.objects.create(user=usuario)
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return cliente


@pytest.fixture
def vendedores(db):
    return Vendedor.objects.create(nome_vendedor="Ana"), Vendedor.objects.create(nome_vendedor="Bruno")


@pytest.fixture
def clientes(vendedores):
    ana, bruno = vendedores
    dados = [
        ("CLI0001", "Mercado Alfa", "Águas Claras", ana),
        ("CLI0002", "Padaria Beta", "Águas Claras", bruno),
        ("CLI0003", "Loja Gama", "Taguatinga", ana),
    ]
    return [Cliente.objects.create(id_cliente=i, razao_social=r, bairro_normalizado=b, vendedor=v)
            for i, r, b, v in dados]
