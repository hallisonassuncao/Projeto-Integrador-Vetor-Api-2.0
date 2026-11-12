-- Consultas úteis. Funcionam no SQLite (arquivo vetor.db) e no PostgreSQL (banco vetor).
-- No VS Code: selecione UMA consulta e execute
--   SQLite (extensão "SQLite"): botão direito > Run Selected Query
--   PostgreSQL (extensão SQLTools): Ctrl+E Ctrl+E

-- 1. Clientes por bairro normalizado (25 grafias viram 4 bairros)
SELECT bairro_normalizado, COUNT(*) AS total
FROM clientes_cliente
GROUP BY bairro_normalizado
ORDER BY total DESC;

-- 2. Bairro e subdivisão
SELECT bairro_normalizado, subdivisao, COUNT(*) AS total
FROM clientes_cliente
GROUP BY bairro_normalizado, subdivisao
ORDER BY bairro_normalizado, subdivisao;

-- 3. Auditoria do bairro: valor original -> valor tratado -> critério e fonte
SELECT cliente_id, valor_original, valor_tratado, criterio, fonte
FROM clientes_auditoria
WHERE campo = 'bairro'
ORDER BY cliente_id;

-- 4. Divergências entre o CEP e o bairro informado
SELECT id_cliente, bairro_informado, cep_normalizado, bairro_normalizado
FROM clientes_cliente
WHERE divergencia_cep_bairro IS TRUE;

-- 5. CEPs bem formatados, mas não encontrados nas APIs (precisa de execução com a API de CEP)
SELECT cliente_id, valor_original AS cep, criterio
FROM clientes_auditoria
WHERE criterio = 'cep_nao_encontrado_na_api'
ORDER BY cliente_id;

-- 6. Clientes que exigem revisão manual
SELECT id_cliente, bairro_informado, bairro_normalizado
FROM clientes_cliente
WHERE revisao_manual IS TRUE;

-- 7. Clientes por vendedor
SELECT v.nome_vendedor, COUNT(*) AS clientes
FROM clientes_cliente c
JOIN clientes_vendedor v ON v.id_vendedor = c.vendedor_id
GROUP BY v.nome_vendedor
ORDER BY clientes DESC;

-- 8. Toda a auditoria de um cliente (troque CLI0002 pelo id desejado)
SELECT campo, valor_original, valor_tratado, criterio, fonte
FROM clientes_auditoria
WHERE cliente_id = 'CLI0002'
ORDER BY id;

-- 9. Linhas de auditoria por campo
SELECT campo, COUNT(*) AS linhas
FROM clientes_auditoria
GROUP BY campo
ORDER BY linhas DESC;
