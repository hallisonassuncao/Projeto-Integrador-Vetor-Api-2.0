def test_front_end_e_servido_na_raiz(client):
    r = client.get("/")
    html = r.content.decode()
    assert r.status_code == 200 and "Distribuidora Vetor" in html
    assert "/api/clientes/bairros/" in html and "/api/auth/token/" in html
    assert "{% verbatim" not in html  # a marcação do Django não vaza para a página
