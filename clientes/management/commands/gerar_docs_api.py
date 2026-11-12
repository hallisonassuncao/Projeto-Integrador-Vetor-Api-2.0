import json

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from drf_spectacular.generators import SchemaGenerator

HTML = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>API Distribuidora Vetor</title>
</head>
<body>
<div id="redoc"></div>
<script>__REDOC__</script>
<script>Redoc.init(__SPEC__, {}, document.getElementById("redoc"));</script>
</body>
</html>
"""


class Command(BaseCommand):
    help = "Gera docs/openapi.yaml e docs/api.html (Redoc em arquivo único, abre sem servidor)."

    def handle(self, *args, **opcoes):
        pasta = settings.BASE_DIR / "docs"
        pasta.mkdir(exist_ok=True)
        call_command("spectacular", "--file", str(pasta / "openapi.yaml"))

        redoc = finders.find("drf_spectacular_sidecar/redoc/bundles/redoc.standalone.js")
        if not redoc:
            raise CommandError("Arquivo do Redoc não encontrado: instale drf-spectacular-sidecar.")
        with open(redoc, encoding="utf-8") as f:
            js = f.read().replace("</script", "<\\/script")
        spec = json.dumps(SchemaGenerator().get_schema(request=None, public=True),
                          ensure_ascii=False).replace("</", "<\\/")
        (pasta / "api.html").write_text(HTML.replace("__REDOC__", js).replace("__SPEC__", spec), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS("Gerados: docs/openapi.yaml e docs/api.html"))
