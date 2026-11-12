# Relatório de trade-offs — ETL Distribuidora Vetor

## Problema
47 clientes com 25 grafias diferentes de bairro (mais 1 registro sem bairro), 4 formatos de telefone,
4 formatos de data, CNPJ com e sem máscara e 34% dos CEPs ausentes ou zerados. Sem tratamento, um
relatório por bairro mostra 25 linhas onde existem 4 bairros.

## O que foi automatizado — e por quê
| Decisão | Motivo |
|---|---|
| Normalização textual determinística (caixa, acento, `DF`, parênteses) | Resolve a maior parte das variantes sem custo nem risco; é reprodutível e testável |
| Dicionário variante → bairro canônico em arquivo CSV | Regra explícita e auditável; quem conhece o negócio amplia sem editar código |
| Padronização de CNPJ, telefone (E.164) e datas | Transformações sem ambiguidade; cada uma gera linha de auditoria |
| Consulta de CEP (ViaCEP → BrasilAPI) com cache | Única fonte externa de verdade geográfica; o cache evita repetir chamadas e torna reexecuções rápidas e estáveis |
| Divergência CEP × bairro: a API prevalece, com flag | Fonte estruturada vence texto livre, mas a decisão fica visível e reversível |

## O que ficou para tratamento manual — e por quê
| Item | Motivo |
|---|---|
| Bairros fora do dicionário e correspondências *fuzzy* | Aproximar texto automaticamente pode juntar bairros diferentes; um erro silencioso contamina o relatório |
| Bairro da API que não existe no dicionário | Pode ser variante nova legítima ou erro da API; só quem conhece a região decide |
| CEPs de outra UF | Indício de erro de cadastro, não de grafia |
| Datas ambíguas (`dd/mm` × `mm/dd`) | Sem segunda fonte não há como confirmar; fica a premissa `dd/mm` + flag `data_ambigua` |
| CNPJ com dígito verificador inválido | Descartar apagaria a base inteira; ficou como sinalização, e a decisão cabe ao negócio |

## Trade-offs principais
1. **Precisão × cobertura.** Preferimos deixar um bairro nulo com revisão a "chutar". O custo é
   trabalho manual residual; o ganho é que nenhum número do relatório depende de adivinhação.
2. **Dependência externa × autonomia.** A API melhora a qualidade, mas pode falhar ou devolver nomes
   fora do padrão. Mitigação: fallback entre dois provedores, cache, falhas nunca cacheadas, e o
   pipeline funciona sem API (`--sem-api`) usando só o dicionário.
3. **Bairro-pai × subdivisão.** Agrupar em "Águas Claras" perde o recorte Sul/Norte; guardá-lo em
   coluna própria permite as duas visões, ao custo de uma coluna a mais.
4. **Rigor × utilidade (CNPJ).** Validar e rejeitar seria o correto em produção, mas aqui geraria
   tabela vazia. Optamos por marcar e documentar o limite.
5. **Carga linha a linha × em lote.** A carga é idempotente (`update_or_create` por `id_cliente`) e
   preserva clientes criados pela API, mas grava registro a registro: adequado ao volume do desafio,
   não a milhões de linhas.
6. **Banco normalizado × tabela larga.** Vendedor ganhou tabela própria, porque a API o exige como
   entidade com CRUD. Bairro e CEP continuam colunas do cliente: simplifica os relatórios agrupados
   por bairro, ao custo de repetir o texto em cada linha.

## Resultado (execução real: ViaCEP + PostgreSQL)
| Indicador | Valor |
|---|---|
| Grafias de bairro → bairros canônicos | 25 (+1 vazio) → **4** (Águas Claras, Taguatinga, Vicente Pires, Guará) |
| CEPs distintos consultados (31 clientes com CEP válido) | 14 (16 requisições, 0 falhas); 2 não encontrados nas APIs |
| Bairro informado e CEP concordam | 27 |
| Divergência CEP × bairro (API prevalece) | 1 (CLI0002) |
| Só o bairro informado, sem confirmação pela API | 18 (15 sem CEP utilizável; 3 com CEP bem formatado, mas inexistente nas APIs) |
| Sem bairro resolvido | 1 (CLI0047, sem bairro nem CEP) |
| Fila de revisão manual após ampliar o dicionário | **0** |
| Linhas de auditoria | 194 (191 + 3 de CEP não encontrado na API) |

- Na **primeira rodada**, 8 clientes foram para revisão manual porque a API devolveu nomes fora do
  dicionário: "Setor Habitacional Vicente Pires" (5) e "Areal" (3). Em todos o bairro informado já
  apontava para o mesmo local. Os dois nomes entraram no dicionário (`Vicente Pires`;
  `Águas Claras / Areal`) e a segunda rodada zerou a fila. É o ciclo esperado do processo:
  automatizar o que o dicionário cobre, revisar o resto, ampliar o dicionário.
- "Areal → Águas Claras" é **premissa assumida** a partir da base (os 3 clientes com esse retorno
  informaram Águas Claras), sem fonte oficial no pipeline.
- CLI0002: informado "Sul (Águas Claras)", ViaCEP devolveu "Taguatinga Norte". A API prevaleceu e o
  caso está registrado na auditoria para conferência; é o único ponto em que o pipeline contrariou o
  cadastro.
- 6 datas ambíguas (lidas como dd/mm); 10 e-mails fora do padrão ASCII sinalizados; 47 CNPJs com
  dígito verificador inválido (base sintética), mantidos e sinalizados.

## Próximos passos
Corrigir os CEPs dos 3 clientes cujo CEP não existe nas APIs (72110-800 e 71900-000), conferir o CLI0002,
decidir a política de CNPJ inválido (quarentena ou rejeição) e, em produção, adotar carga incremental.
