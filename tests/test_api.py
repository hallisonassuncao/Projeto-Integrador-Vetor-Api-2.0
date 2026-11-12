import pytest
from django.contrib import admin

from clientes.models import Auditoria, Cliente, Vendedor

pytestmark = pytest.mark.django_db


# ------------------------------------------------------- controle de acesso
def test_leitura_publica(api, clientes):
    r = api.get("/api/clientes/")
    assert r.status_code == 200 and r.json()["count"] == 3
    assert api.get("/api/clientes/CLI0001/").status_code == 200
    assert api.get("/api/vendedores/").status_code == 200


@pytest.mark.parametrize("metodo,url", [
    ("post", "/api/clientes/"), ("put", "/api/clientes/CLI0001/"),
    ("patch", "/api/clientes/CLI0001/"), ("delete", "/api/clientes/CLI0001/"),
    ("post", "/api/vendedores/"), ("delete", "/api/vendedores/1/"),
])
def test_escrita_exige_login(api, clientes, metodo, url):
    assert getattr(api, metodo)(url, {}, format="json").status_code == 401


def test_token_valido_e_invalido(api, api_auth):
    ok = api.post("/api/auth/token/", {"username": "tester", "password": "senha-forte-123"}, format="json")
    assert ok.status_code == 200 and ok.json()["token"]
    ruim = api.post("/api/auth/token/", {"username": "tester", "password": "errada"}, format="json")
    assert ruim.status_code == 400


# ---------------------------------------------------------- CRUD de clientes
def test_criar_cliente_normaliza_e_gera_id(api_auth, vendedores):
    r = api_auth.post("/api/clientes/", {
        "razao_social": "Nova Loja", "cnpj_normalizado": "11222333000181",
        "telefone_normalizado": "(61) 98433-1053", "bairro_normalizado": "aguas claras",
        "cep_normalizado": "71926750", "data_cadastro_normalizado": "2024-05-10",
        "email": "contato@novaloja.com.br", "vendedor_id": vendedores[0].id_vendedor,
    }, format="json")
    assert r.status_code == 201, r.json()
    corpo = r.json()
    assert corpo["id_cliente"] == "CLI0001"
    assert corpo["cnpj_normalizado"] == "11.222.333/0001-81"
    assert corpo["telefone_normalizado"] == "+5561984331053"
    assert corpo["bairro_normalizado"] == "Águas Claras"
    assert corpo["cep_normalizado"] == "71926-750"
    assert corpo["vendedor_id"] == vendedores[0].id_vendedor


def test_criar_cliente_proximo_id_segue_a_sequencia(api_auth, clientes, vendedores):
    r = api_auth.post("/api/clientes/", {"razao_social": "X", "vendedor_id": vendedores[0].id_vendedor},
                      format="json")
    assert r.json()["id_cliente"] == "CLI0004"


@pytest.mark.parametrize("campo,valor", [
    ("cnpj_normalizado", "123"), ("telefone_normalizado", "12345"), ("cep_normalizado", "00000-000"),
])
def test_validacoes_de_entrada(api_auth, vendedores, campo, valor):
    r = api_auth.post("/api/clientes/", {"razao_social": "X", campo: valor,
                                         "vendedor_id": vendedores[0].id_vendedor}, format="json")
    assert r.status_code == 400 and campo in r.json()


def test_vendedor_inexistente_e_id_duplicado(api_auth, clientes):
    r = api_auth.post("/api/clientes/", {"razao_social": "X", "vendedor_id": 9999}, format="json")
    assert r.status_code == 400 and "vendedor_id" in r.json()
    r = api_auth.post("/api/clientes/", {"id_cliente": "CLI0001", "razao_social": "X",
                                         "vendedor_id": clientes[0].vendedor_id}, format="json")
    assert r.status_code == 400 and "id_cliente" in r.json()


def test_editar_e_excluir_cliente(api_auth, clientes):
    r = api_auth.patch("/api/clientes/CLI0001/", {"razao_social": "Alfa Atualizado"}, format="json")
    assert r.status_code == 200 and r.json()["razao_social"] == "Alfa Atualizado"
    r = api_auth.put("/api/clientes/CLI0001/", {"razao_social": "Alfa PUT",
                                                "vendedor_id": clientes[0].vendedor_id}, format="json")
    assert r.status_code == 200
    r = api_auth.patch("/api/clientes/CLI0001/", {"id_cliente": "CLI7777"}, format="json")
    assert r.status_code == 400
    assert api_auth.delete("/api/clientes/CLI0001/").status_code == 204
    assert not Cliente.objects.filter(pk="CLI0001").exists()


def test_cliente_inexistente_404(api):
    assert api.get("/api/clientes/CLI0000/").status_code == 404


# -------------------------------------------------------- rotas de relacionamento
@pytest.mark.parametrize("nome,esperado", [
    ("Águas Claras", 2), ("aguas%20claras", 2), ("AGUAS%20CLARAS", 2), ("Taguatinga", 1), ("Inexistente", 0),
])
def test_clientes_por_bairro(api, clientes, nome, esperado):
    r = api.get(f"/api/clientes/bairro/{nome}/")
    assert r.status_code == 200 and r.json()["count"] == esperado


def test_resumo_por_bairro(api, clientes):
    r = api.get("/api/clientes/bairros/")
    assert r.status_code == 200
    assert r.json() == [{"bairro_normalizado": "Águas Claras", "total": 2},
                        {"bairro_normalizado": "Taguatinga", "total": 1}]


def test_clientes_por_vendedor_nas_duas_rotas(api, clientes, vendedores):
    ana = vendedores[0].id_vendedor
    a = api.get(f"/api/clientes/vendedor/{ana}/").json()
    b = api.get(f"/api/vendedores/{ana}/clientes/").json()
    assert a["count"] == b["count"] == 2
    assert {c["id_cliente"] for c in a["results"]} == {"CLI0001", "CLI0003"}
    assert api.get("/api/clientes/vendedor/9999/").status_code == 404
    assert api.get("/api/vendedores/9999/clientes/").status_code == 404


# ------------------------------------------------------ CRUD de vendedores
def test_crud_de_vendedores(api_auth, api):
    r = api_auth.post("/api/vendedores/", {"nome_vendedor": "Carla"}, format="json")
    assert r.status_code == 201
    vid = r.json()["id_vendedor"]
    assert api_auth.post("/api/vendedores/", {"nome_vendedor": "Carla"}, format="json").status_code == 400
    assert api_auth.patch(f"/api/vendedores/{vid}/", {"nome_vendedor": "Carla S."}, format="json").status_code == 200
    assert api.get(f"/api/vendedores/{vid}/").json()["nome_vendedor"] == "Carla S."
    assert api_auth.delete(f"/api/vendedores/{vid}/").status_code == 204


def test_vendedor_com_clientes_nao_pode_ser_excluido(api_auth, clientes, vendedores):
    r = api_auth.delete(f"/api/vendedores/{vendedores[0].id_vendedor}/")
    assert r.status_code == 409
    assert Vendedor.objects.filter(pk=vendedores[0].pk).exists()


# ----------------------------------------------------- documentação e admin
def test_documentacao_redoc_e_schema(api):
    docs = api.get("/api/docs/")
    assert docs.status_code == 200 and b"redoc" in docs.content.lower()
    schema = api.get("/api/schema/")
    assert schema.status_code == 200 and b"openapi" in schema.content


def test_schema_openapi_valido_sem_avisos(tmp_path):
    from django.core.management import call_command
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(tmp_path / "schema.yml"))
    texto = (tmp_path / "schema.yml").read_text(encoding="utf-8")
    for rota in ("/api/clientes/", "/api/clientes/{id_cliente}/", "/api/clientes/bairro/{nome}/",
                 "/api/clientes/vendedor/{vendedor_id}/", "/api/vendedores/",
                 "/api/vendedores/{id_vendedor}/clientes/", "/api/auth/token/"):
        assert rota in texto, rota


def test_todas_as_tabelas_no_admin():
    for modelo in (Cliente, Vendedor, Auditoria):
        assert admin.site.is_registered(modelo)


def test_auditoria_nao_e_exposta_na_api(api):
    assert api.get("/api/auditoria/").status_code == 404


def test_redoc_e_swagger_usam_arquivos_locais_sem_cdn(api):
    from django.contrib.staticfiles import finders

    docs = api.get("/api/docs/").content.decode()
    assert "cdn.jsdelivr" not in docs and "/static/drf_spectacular_sidecar/redoc" in docs
    assert finders.find("drf_spectacular_sidecar/redoc/bundles/redoc.standalone.js")
    swagger = api.get("/api/swagger/")
    assert swagger.status_code == 200 and b"cdn.jsdelivr" not in swagger.content


def test_gera_documentacao_estatica_da_api(settings, tmp_path):
    from django.core.management import call_command

    settings.BASE_DIR = tmp_path
    call_command("gerar_docs_api")
    html = (tmp_path / "docs" / "api.html").read_text(encoding="utf-8")
    assert "Redoc.init(" in html and "/api/clientes/bairro/{nome}/" in html and "Token SEU_TOKEN" in html
    assert (tmp_path / "docs" / "openapi.yaml").read_text(encoding="utf-8").startswith("openapi:")
