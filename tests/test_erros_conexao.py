import pytest

from config.erros import mensagem_de_conexao, tratar_erro_de_conexao

SERVIDOR = 'FATAL:  a autenticação do tipo senha falhou para o usuário "postgres"'


def erro_do_servidor():
    """Reproduz o que o psycopg2 faz: tenta ler como UTF-8 bytes em Windows-1252."""
    dados = SERVIDOR.encode("cp1252")
    with pytest.raises(UnicodeDecodeError) as info:
        dados.decode("utf-8")
    return info.value


def test_recupera_a_mensagem_real_do_servidor():
    assert "autenticação do tipo senha falhou" in mensagem_de_conexao(erro_do_servidor())


def test_encerra_com_mensagem_clara_e_sem_traceback():
    with pytest.raises(SystemExit) as info:
        tratar_erro_de_conexao(erro_do_servidor())
    texto = str(info.value)
    assert "autenticação do tipo senha falhou" in texto and "DB_PASSWORD" in texto and ".env" in texto


def test_outro_erro_de_decodificacao_nao_e_escondido():
    outro = UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 1, "invalid start byte")
    assert mensagem_de_conexao(outro) is None
    with pytest.raises(UnicodeDecodeError):
        tratar_erro_de_conexao(outro)
