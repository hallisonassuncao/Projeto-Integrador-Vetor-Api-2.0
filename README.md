## 🏬 Distribuidora Vetor — ETL + API REST (Desafio Primora)

Projeto do desafio Primora (Bolsa Futuro Digital), em duas partes:

1. **Parte 1 — ETL:** lê a base de clientes (CSV), normaliza bairro, CEP, CNPJ, telefone, data e e-mail,
   enriquece com ViaCEP/BrasilAPI (com cache local), grava no banco e registra uma trilha de auditoria
   (valor original → valor tratado → critério/fonte).
2. **Parte 2 — API REST em Django (DRF):** consulta pública (GET) e operações restritas a usuários
   autenticados (token), com documentação OpenAPI em Redoc.

## Escopo do desafio — Parte 1 (ETL)

### Entregáveis esperados

| Entregável esperado | Como foi atendido | Onde está |
|---|---|---|
| Pipeline de ETL (Python) com etapas claras de extração, transformação e carga | Três etapas separadas (`extrair`, `transformar`, `carregar_no_banco`), executadas por `python manage.py rodar_etl` | `etl/pipeline.py`, `clientes/etl_service.py` |
| Base final tratada, persistida em banco SQL | Clientes e vendedores no PostgreSQL (ou SQLite) | Tabelas `clientes_cliente` e `clientes_vendedor` |
| Tabela ou log de auditoria: valor original → valor tratado → critério/fonte da decisão | Uma linha por alteração ou critério diferente de "ok"; também exportada em CSV com `--saida` | Tabela `clientes_auditoria` (admin) e `saida/auditoria_tratamento.csv` |
| Testes automatizados da lógica de normalização (chamadas externas simuladas, não reais) | 121 testes; ViaCEP e BrasilAPI simuladas, sem rede | `tests/` (`pytest`) |
| Documentação técnica explicando as regras adotadas e seus limites conhecidos | Regras por campo, critério de divergência, limites e o que foi verificado | [docs/DOCUMENTACAO_TECNICA.md](docs/DOCUMENTACAO_TECNICA.md) |
| Relatório curto (1-2 páginas) com os trade-offs: o que foi automatizado, o que foi tratado manualmente, e por quê | Cerca de 800 palavras, com os números da execução real | [docs/RELATORIO_TRADEOFFS.md](docs/RELATORIO_TRADEOFFS.md) |

### Abordagens sugeridas e o que a equipe adotou

O enunciado trata as abordagens como pontos de partida, não como roteiro obrigatório.

| Abordagem possível | Decisão da equipe | Onde está |
|---|---|---|
| Normalização textual determinística (caixa, acentuação, espaços, conteúdo entre parênteses) | Adotada: chave em minúsculas, sem acento, sem parênteses, sem sufixo "DF" e sem pontuação | `etl/normalizers.py` (`chave_texto`) |
| Dicionário de correspondência (variante → nome canônico), construído e ampliado ao longo do processo | Adotada: dicionário em CSV, ampliado após a execução real com "Areal" e "Setor Habitacional Vicente Pires" | `etl/dicionario_bairros.csv` |
| Enriquecimento via API pública gratuita de CEP (ViaCEP, BrasilAPI), com cache local | Adotada: ViaCEP, com BrasilAPI de reserva; cache em SQLite, inclusive para "CEP não existe" (falhas de rede não são cacheadas) | `etl/cep_client.py` |
| Critério explícito para divergências entre o bairro informado e o retornado pelo CEP | Adotada: a API prevalece e a divergência é sinalizada e auditada; sem confirmação da API, vale o bairro informado normalizado | `etl/resolucao.py`, documentação técnica (seção 3.3) |
| Tratamento de campos adicionais sujos (telefone, CNPJ, datas) | Adotada: CNPJ formatado e validado, telefone em E.164, datas em 4 formatos (lidas como dd/mm) e e-mail validado. Valores inválidos são sinalizados, não descartados | `etl/normalizers.py` |

As regras de negócio assumidas pela equipe (por exemplo, datas ambíguas lidas como dd/mm e a subdivisão
guardada em coluna própria) estão documentadas na documentação técnica, junto com os limites conhecidos.

## Escopo do desafio — Parte 2 (API)

| Item | Onde está |
|---|---|
| CRUD de clientes e vendedores, rotas por bairro e por vendedor | `clientes/views.py`, `config/urls.py` |
| Autenticação por token e controle de acesso (logado: CRUD; não logado: só GET) | `POST /api/auth/token/` |
| Documentação da API (OpenAPI/Redoc) | `/api/docs/`, `/api/schema/` e, sem servidor, [docs/api.html](docs/api.html) |
| Admin com todas as tabelas | `clientes/admin.py` |
| Migrações | `clientes/migrations/` |
| Modelo de dados (MER + DER) | [docs/MODELO_DE_DADOS.md](docs/MODELO_DE_DADOS.md) |
| README | Este arquivo |

## Requisitos

- Python 3.10 ou mais novo (Django 6 exige 3.12+; em versões anteriores o pip instala o Django 5.2)
- PostgreSQL (opcional: sem configuração, o projeto usa SQLite, no arquivo `vetor.db`)

## 🛠 Instalação

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows (PowerShell)
source .venv/bin/activate           # Linux/macOS

# 2. Instalar os pacotes
pip install -r requirements.txt

# 3. Configurar o ambiente: copie .env.example para .env e informe a senha do PostgreSQL
#    (se DB_NAME não estiver no .env, o projeto usa SQLite no arquivo vetor.db)
copy .env.example .env              # Windows   |   cp .env.example .env   # Linux/macOS

# 4. Criar as tabelas
python manage.py migrate

# 5. Rodar o ETL (carrega clientes, vendedores e auditoria)
python manage.py rodar_etl                 # com consulta de CEP (internet)
python manage.py rodar_etl --sem-api       # offline, só com o dicionário de bairros
python manage.py rodar_etl --saida saida   # além do banco, exporta clientes e auditoria em CSV

# 6. Criar um usuário (admin e escrita na API)
python manage.py createsuperuser

# 6.1 Observação Importante

Utilize os procedimentos abaixo caso ocorra um erro ao criar o usuário **admin** (necessário para acesso administrativo e gravação na API).

## Exemplo de erro

Se a seguinte mensagem for exibida:

Usuário (leave blank to use 'halli'): admin

Error: That username is already taken.

Isso significa que o usuário **admin** já existe no banco de dados.

## Verificando a senha do usuário existente

Acesse o shell do Django:

python manage.py shell

Quando o prompt >>> for exibido, execute:

from django.contrib.auth.models import User

u = User.objects.get(username="admin")

u.check\_password("projeto123")

O resultado será:

- True → a senha é projeto123;
- False → a senha é diferente de projeto123.

---

# 6.2 Redefinir a senha do usuário admin

Caso a senha não seja conhecida ou esteja incorreta, execute:

python manage.py changepassword admin

O Django solicitará:

Changing password for user 'admin'

Password:

Password (again):

Digite a nova senha e confirme\-a quando solicitado.

Após a alteração, utilize a nova senha para acessar o painel administrativo e os recursos que dependem do usuário **admin**.

==> Você também pode verificar todos os usuários cadastrados:

python manage.py shell

from django.contrib.auth.models import User
print(list(User.objects.values('id', 'username', 'is_staff', 'is_superuser')))

Se o retorno vier vazio ([]), não existe nenhum usuário cadastrado no banco.
```

O ETL é idempotente: pode ser reexecutado sem duplicar dados e não apaga clientes criados pela API.
O arquivo `.env` guarda a senha e **não vai para o Git** (está no `.gitignore`).

## Rodar pelo VS Code

O projeto traz a pasta `.vscode` com as configurações prontas.

1. Abra a pasta do projeto (a que contém o `manage.py`) em *Arquivo → Abrir Pasta*.
2. Escolha o interpretador: `Ctrl+Shift+P` → *Python: Select Interpreter* → o do ambiente virtual onde você
   instalou os pacotes (termina em `.venv\Scripts\python.exe`). Se ele não aparecer na lista, use *Enter interpreter path...*.
3. Para rodar o ETL etapa por etapa: abra `executar_etl.py` e clique em **Run Python File** (▶), ou use **F5**.
   Ele mostra a extração, a transformação e a carga, uma de cada vez, e depois o resumo.
4. Em **Executar e Depurar** (`Ctrl+Shift+D`) há uma configuração para cada tarefa:

| Configuração | O que faz |
|---|---|
| ETL - 3 etapas (com API de CEP) | `executar_etl.py`, consultando ViaCEP/BrasilAPI |
| ETL - 3 etapas (offline, sem API) | `executar_etl.py --sem-api` |
| ETL - comando Django (rodar_etl + CSV) | `manage.py rodar_etl --saida saida` |
| Banco - migrate | `manage.py migrate` |
| API - runserver | Sobe a API em http://127.0.0.1:8000 |
| Testes - pytest | Roda os testes |

Os testes também aparecem no painel **Testing** do VS Code. Antes do primeiro ETL, rode a configuração
*Banco - migrate* (ou `python manage.py migrate`).

## Banco SQLite (arquivo vetor.db)

Sem `DB_NAME` no `.env`, o projeto grava no arquivo `vetor.db`, na pasta do projeto, sem precisar de servidor.
Para gerar o `vetor.db` mesmo com o PostgreSQL configurado no `.env`, force o SQLite só naquele terminal:

```powershell
$env:DB_ENGINE="sqlite"
python manage.py migrate
python manage.py rodar_etl --saida saida
```

As tabelas do projeto são `clientes_cliente`, `clientes_vendedor` e `clientes_auditoria`, além das tabelas
do próprio Django (usuários, tokens e sessões). O arquivo `vetor.db` não vai para o Git (está no `.gitignore`).
Para ver o conteúdo:

```powershell
python -c "import sqlite3; c=sqlite3.connect('vetor.db'); print(c.execute('SELECT bairro_normalizado, COUNT(*) FROM clientes_cliente GROUP BY 1').fetchall())"
```

## Consultar o banco no VS Code

Ao abrir a pasta, o VS Code sugere instalar as extensões recomendadas (`.vscode/extensions.json`). O arquivo
[consultas.sql](consultas.sql) traz 9 consultas prontas (bairros agrupados, auditoria, divergências, vendedores).

**SQLite (arquivo `vetor.db`, o mais simples):**

1. Gere o arquivo: `$env:DB_ENGINE="sqlite"`, depois `python manage.py migrate` e `python manage.py rodar_etl`.
2. Instale a extensão **SQLite** (alexcvzz) e use `Ctrl+Shift+P` → *SQLite: Open Database* → escolha `vetor.db`.
   O painel **SQLITE EXPLORER** passa a listar o banco e as tabelas. Para consultar: abra `consultas.sql`,
   selecione uma consulta e use botão direito → *Run Selected Query*.
3. Para só ver as tabelas, a extensão **SQLite Viewer** (qwtel) abre o `vetor.db` com um clique.

**PostgreSQL (banco `vetor`):** instale **SQLTools** e **SQLTools PostgreSQL/Cockroach Driver**. A conexão
`vetor (PostgreSQL)` já está configurada em `.vscode/settings.json` e pede a senha ao conectar (ela não fica
salva no arquivo). Conecte pelo ícone do SQLTools na barra lateral e rode as consultas com `Ctrl+E Ctrl+E`.

As tabelas do projeto são `clientes_cliente`, `clientes_vendedor` e `clientes_auditoria`.

## Interface web (front end)

Com o servidor ligado, abra **http://127.0.0.1:8000/**. A interface usa só a API do projeto:

| Tela | O que faz | API usada |
|---|---|---|
| Painel | Total de clientes, faixa com a proporção por bairro e clientes por vendedor | `/api/clientes/bairros/`, `/api/clientes/`, `/api/vendedores/` |
| Clientes | Busca, filtro por bairro e por vendedor, detalhes | `/api/clientes/bairro/{nome}/`, `/api/clientes/vendedor/{id}/` |
| Vendedores | Lista com a quantidade de clientes de cada um | `/api/vendedores/` |

Sem login a interface é somente leitura (só GET). Ao clicar em **Entrar para editar**, ela pede usuário e senha, obtém o
token em `/api/auth/token/` e libera criar, editar e excluir clientes e vendedores. O arquivo da interface é
`clientes/templates/app.html` (HTML, CSS e JavaScript em um só arquivo, sem etapa de build).

## Rodar o servidor

```bash
python manage.py runserver
```

| Endereço | O que é |
|---|---|
| http://127.0.0.1:8000/ | Interface web (painel, clientes e vendedores) |
| http://127.0.0.1:8000/api/docs/ | Documentação interativa (Redoc, arquivos locais) |
| http://127.0.0.1:8000/api/swagger/ | Mesma documentação em Swagger UI (alternativa) |
| http://127.0.0.1:8000/api/schema/ | Schema OpenAPI (drf-spectacular) |
| http://127.0.0.1:8000/admin/ | Admin: Clientes, Vendedores e Auditoria |

A documentação também existe em arquivo único, que abre com duplo clique e **sem servidor**: [docs/api.html](docs/api.html) (schema em [docs/openapi.yaml](docs/openapi.yaml)). Para regenerá-la depois de mudar a API: `python manage.py gerar_docs_api`.

## Endpoints

| Método e rota | Descrição | Acesso |
|---|---|---|
| `GET/POST /api/clientes/` | Listar / criar clientes | GET público, POST autenticado |
| `GET/PUT/PATCH/DELETE /api/clientes/{id}/` | Detalhar, editar, excluir | GET público, demais autenticados |
| `GET /api/clientes/bairro/{nome}/` | Clientes de um bairro (aceita variações: `aguas claras`) | Público |
| `GET /api/clientes/bairros/` | Total de clientes por bairro normalizado | Público |
| `GET /api/clientes/vendedor/{id}/` | Clientes de um vendedor | Público |
| `GET/POST /api/vendedores/` | Listar / criar vendedores | GET público, POST autenticado |
| `GET/PUT/PATCH/DELETE /api/vendedores/{id}/` | Detalhar, editar, excluir | GET público, demais autenticados |
| `GET /api/vendedores/{id}/clientes/` | Clientes de um vendedor | Público |
| `POST /api/auth/token/` | Obter token (`username` e `password`) | Público |

A auditoria não é exposta na API, só no admin. As listas são paginadas (50 por página).

### Autenticação

```powershell
# PowerShell: obter o token e criar um cliente (id_cliente é gerado se omitido)
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/token/ `
     -ContentType "application/json" -Body '{"username":"admin","password":"SUA_SENHA"}'
$h = @{ Authorization = "Token $($r.token)" }
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/clientes/ -Headers $h `
     -ContentType "application/json" `
     -Body '{"razao_social":"Loja Nova","vendedor_id":1,"bairro_normalizado":"aguas claras"}'
```

```bash
# curl  ==> No PowerShell
$body = @{
    username = "admin"
    password = "SUA_SENHA"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/auth/token/" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

Na criação e edição, CNPJ, telefone, CEP e bairro passam pelas mesmas normalizações do ETL
(CNPJ `XX.XXX.XXX/XXXX-XX`, telefone E.164, CEP `NNNNN-NNN`, bairro canônico). Um vendedor com
clientes vinculados não pode ser excluído (resposta 409).

## Testes

```bash
pytest
```

121 testes (ETL e API). Não usam rede (as APIs de CEP são simuladas) e rodam em SQLite.

## Estrutura

```
executar_etl.py    ETL etapa por etapa (roda direto no VS Code)
consultas.sql      consultas prontas (SQLite e PostgreSQL)
config/            configurações e urls
clientes/          modelos, serializers, views (API), admin, carga do ETL, comando rodar_etl, interface web (templates/app.html)
etl/               normalização, consulta de CEP com cache, regras de decisão, dicionário de bairros
data/              base de clientes (CSV)
tests/             testes do ETL e da API
.vscode/           configurações do VS Code (executar, depurar e testar)
docs/              MER + DER, documentação técnica do ETL, relatório de trade-offs
```

## Problemas comuns

- **Erro ao conectar no PostgreSQL (Windows):** quase sempre é senha ou usuário incorretos no `.env`. O projeto
  mostra a mensagem real do servidor (por exemplo, "autenticação do tipo senha falhou"). Confira `DB_PASSWORD`
  e salve o arquivo.
- **`/api/docs/` em branco:** a página precisa dos arquivos estáticos do Redoc. Rode `python -m pip install -r requirements.txt`
  (inclui `drf-spectacular-sidecar`), reinicie o servidor e use `Ctrl+F5` no navegador. A alternativa é `/api/swagger/`.
- **`No module named ...`:** o ambiente virtual não está ativo ou os pacotes não foram instalados.
- **`manage.py` não encontrado:** execute os comandos dentro da pasta do projeto.
  

## 👥 Autoria
- Autores: Aleandreson, Hallison, Bruno Miranda e Cecília
- Projeto: Desafio Primora
- Área: Desenvolvimento de Software BackEnd - Python com Django
- Instituição: Instituto Federal de Brasília (IFB)
  
