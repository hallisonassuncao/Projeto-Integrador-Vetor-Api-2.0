import pytest

from executar_etl import main

pytestmark = pytest.mark.django_db


def test_script_mostra_as_tres_etapas_e_grava_no_banco(capsys, tmp_path):
    main(["--sem-api", "--saida", str(tmp_path)])
    saida = capsys.readouterr().out
    assert "1. EXTRAÇÃO" in saida and "2. TRANSFORMAÇÃO" in saida and "3. CARGA" in saida
    assert "47 registros lidos do CSV" in saida
    assert "47 clientes, 5 vendedores" in saida
    assert (tmp_path / "clientes_tratados.csv").exists()
    assert (tmp_path / "auditoria_tratamento.csv").exists()
