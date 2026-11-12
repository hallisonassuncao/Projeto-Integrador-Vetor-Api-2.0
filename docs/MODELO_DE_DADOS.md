# Modelo de dados (MER + DER)

Os diagramas usam Mermaid e são renderizados automaticamente pelo GitHub.

## MER — modelo conceitual

Entidades do negócio e seus relacionamentos, sem decisões de implementação.

```mermaid
erDiagram
  BAIRRO |o--o{ CLIENTE : "localiza"
  CEP |o--o{ CLIENTE : "identifica"
  VENDEDOR ||--o{ CLIENTE : "atende"
  CLIENTE ||--o{ AUDITORIA : "tem tratamentos"
  BAIRRO ||--o{ VARIANTE_BAIRRO : "e grafado como"
  CLIENTE {
    texto id_cliente PK
    texto razao_social
    texto cnpj
    texto telefone
    texto email
    data data_cadastro
  }
  BAIRRO {
    texto nome PK
  }
  CEP {
    texto cep PK
    texto bairro_retornado
    texto localidade
    texto uf
  }
  VENDEDOR {
    numero id PK
    texto nome
  }
  VARIANTE_BAIRRO {
    texto variante PK
    texto subdivisao
  }
  AUDITORIA {
    numero id PK
    texto campo
    texto valor_original
    texto valor_tratado
    texto criterio
    data executado_em
  }
```

Leitura das cardinalidades:

- Um cliente tem no máximo um bairro e no máximo um CEP (o CLI0047 não tem nenhum dos dois). Um CEP serve a vários clientes: na base há 14 CEPs válidos distintos, 10 deles compartilhados.
- Cada cliente tem exatamente um vendedor; um vendedor atende vários clientes.
- Cada cliente tem vários registros de auditoria (valor original → valor tratado → critério).
- Cada bairro canônico pode ser escrito de várias formas (dicionário de variantes).

## DER — modelo lógico (banco relacional)

Tabelas criadas pelas migrações do Django. Os nomes físicos são `clientes_vendedor`,
`clientes_cliente` e `clientes_auditoria`.

```mermaid
erDiagram
  VENDEDOR ||--o{ CLIENTE : "vendedor_id"
  CLIENTE ||--o{ AUDITORIA : "cliente_id"
  CLIENTE }o..o| CEP_CACHE : "consulta por cep"
  DICIONARIO_BAIRROS |o..o{ CLIENTE : "traduz bairro"
  VENDEDOR {
    serial id_vendedor PK
    varchar(100) nome_vendedor UK
  }
  CLIENTE {
    varchar(20) id_cliente PK
    varchar(200) razao_social
    varchar(18) cnpj_normalizado
    varchar(15) telefone_normalizado
    varchar(150) email
    varchar(100) bairro_normalizado
    varchar(9) cep_normalizado
    date data_cadastro_normalizado
    integer vendedor_id FK
    varchar(80) cidade
    varchar(2) uf
    varchar(100) bairro_informado
    varchar(30) subdivisao
    varchar(30) bairro_fonte
    varchar(30) cep_status
    varchar(10) telefone_tipo
    boolean cnpj_dv_valido
    boolean email_valido
    boolean divergencia_cep_bairro
    boolean revisao_manual
    boolean data_ambigua
  }
  AUDITORIA {
    bigserial id PK
    varchar(20) cliente_id FK
    varchar(30) campo
    text valor_original
    text valor_tratado
    text criterio
    varchar(30) fonte
    boolean revisao_manual
    timestamptz executado_em
  }
  CEP_CACHE {
    text cep PK
    integer encontrado
    text bairro
    text localidade
    text uf
    text fonte
    text consultado_em
  }
  DICIONARIO_BAIRROS {
    text variante PK
    text bairro
    text subdivisao
  }
```

### Como o MER vira o DER

| Entidade conceitual | Implementação |
|---|---|
| Vendedor | Tabela própria `clientes_vendedor` (exigida pela API) |
| Cliente | Tabela `clientes_cliente`, com FK `vendedor_id` (`ON DELETE PROTECT`) |
| Bairro e CEP | Colunas `bairro_normalizado` e `cep_normalizado` do cliente. Desnormalização intencional: a base é voltada a relatórios agrupados por bairro |
| Auditoria | Tabela `clientes_auditoria`, com FK real para o cliente (`ON DELETE CASCADE`). Aparece só no admin, não na API |
| Variante de bairro | Arquivo `etl/dicionario_bairros.csv`, fora do banco |
| Cache de CEP | Arquivo SQLite local `cache/cep_cache.sqlite`, fora do banco |

As colunas depois de `vendedor_id` na tabela de cliente são metadados do ETL: aparecem no admin
e não são expostas na API.
