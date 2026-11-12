#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    try:
        execute_from_command_line(sys.argv)
    except UnicodeDecodeError as erro:
        from config.erros import tratar_erro_de_conexao
        tratar_erro_de_conexao(erro)


if __name__ == "__main__":
    main()
