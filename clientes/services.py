"""Regras de normalização reutilizadas pela API (mesmas funções do ETL)."""
from functools import lru_cache

from etl.normalizers import (carregar_dicionario, normalizar_bairro, normalizar_cep,
                             normalizar_cnpj, normalizar_telefone)


@lru_cache(maxsize=1)
def _dicionario():
    return carregar_dicionario()


def bairro_canonico(texto: str | None) -> str | None:
    """Devolve o bairro canônico para qualquer grafia conhecida (ou None se desconhecida)."""
    return normalizar_bairro(texto, _dicionario()).bairro


def normalizar_bairro_entrada(valor):
    if not valor or not valor.strip():
        return None
    return bairro_canonico(valor) or " ".join(valor.split())


def normalizar_cnpj_entrada(valor):
    if not valor or not valor.strip():
        return None
    formatado, _, _ = normalizar_cnpj(valor)
    if formatado is None:
        raise ValueError("CNPJ deve ter 14 dígitos.")
    return formatado


def normalizar_telefone_entrada(valor):
    if not valor or not valor.strip():
        return None
    e164, _, _ = normalizar_telefone(valor)
    if e164 is None:
        raise ValueError("Telefone inválido: informe DDD + número (10 ou 11 dígitos).")
    return e164


def normalizar_cep_entrada(valor):
    if not valor or not valor.strip():
        return None
    cep, _ = normalizar_cep(valor)
    if cep is None:
        raise ValueError("CEP inválido: informe 8 dígitos.")
    return cep
