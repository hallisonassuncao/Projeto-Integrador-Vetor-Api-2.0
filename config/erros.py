"""Traduz o erro obscuro de conexão do PostgreSQL no Windows (UnicodeDecodeError) em uma mensagem clara.

Quando a conexão é recusada (senha errada, usuário ou banco inexistente), o servidor responde em
português com acentos em Windows-1252, e o driver tenta ler como UTF-8 e falha. Os bytes originais
continuam no erro, então dá para decodificá-los e mostrar a mensagem real do servidor.
"""
import sys

PALAVRAS = ("fatal", "senha", "password", "autentica", "banco de dados", "database", "role", "usu")


def mensagem_de_conexao(erro):
    """Devolve o texto do servidor se o erro veio de uma conexão recusada; senão, None."""
    if erro.encoding.lower().replace("-", "") != "utf8":
        return None
    texto = bytes(erro.object).decode("cp1252", errors="replace").strip()
    return texto if any(p in texto.lower() for p in PALAVRAS) else None


def tratar_erro_de_conexao(erro):
    """Encerra com uma mensagem clara; se não for erro de conexão, propaga o erro original."""
    texto = mensagem_de_conexao(erro)
    if texto is None:
        raise erro
    sys.exit(
        "\nERRO ao conectar no PostgreSQL.\n"
        f"Mensagem do servidor: {texto}\n\n"
        "Confira DB_USER, DB_PASSWORD e DB_NAME no arquivo .env (salve o arquivo depois de editar).\n"
        'Para usar o SQLite enquanto isso, rode antes: $env:DB_ENGINE="sqlite"  (PowerShell)\n'
    )
