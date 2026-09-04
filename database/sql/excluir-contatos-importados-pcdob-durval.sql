-- Exclusão lógica dos cadastros importados da fonte "Filiados PCdoB - Durval".
-- Espelha o comportamento de DELETE /api/v1/cadastro/pessoas/{id} (deactivate_person).
--
-- Campos persistidos em cadastro.pessoa:
--   ativo = FALSE
--   excluido_em = now()
--   atualizado_em = now()
--   atualizado_por = <usuario responsável> (opcional; NULL se operação manual)
--
-- Contatos, documentos, endereços e demais vínculos filhos NÃO são alterados.
-- A pessoa deixa de aparecer nas consultas que filtram excluido_em IS NULL.

-- 1) Conferir quantidade antes (esperado: 16457)
SELECT COUNT(*) AS total_ativos
  FROM cadastro.pessoa p
  JOIN etl.fonte_dado f ON f.id = p.fonte_dado_id
 WHERE f.nome = 'Filiados PCdoB - Durval'
   AND p.excluido_em IS NULL;

-- 2) Pré-visualização (mesmo critério da listagem)
SELECT p.id,
       p.nome_completo,
       CASE WHEN p.sexo = 'M' THEN 'Masculino' ELSE 'Feminino' END AS sexo,
       pce.valor AS email,
       pct.valor AS telefone,
       pcw.valor AS whatsapp
  FROM cadastro.pessoa p
  JOIN etl.fonte_dado f ON f.id = p.fonte_dado_id
  LEFT JOIN cadastro.pessoa_contato pce
         ON p.id = pce.pessoa_id AND pce.tipo_contato = 'email'
  LEFT JOIN cadastro.pessoa_contato pct
         ON p.id = pct.pessoa_id AND pct.tipo_contato = 'telefone'
  LEFT JOIN cadastro.pessoa_contato pcw
         ON p.id = pcw.pessoa_id AND pcw.tipo_contato = 'whatsapp'
 WHERE f.nome = 'Filiados PCdoB - Durval'
   AND p.excluido_em IS NULL;

-- 3) Exclusão lógica
BEGIN;

UPDATE cadastro.pessoa p
   SET ativo = FALSE,
       excluido_em = now(),
       atualizado_em = now(),
       atualizado_por = NULL -- substitua pelo id do usuário responsável, se desejar
  FROM etl.fonte_dado f
 WHERE f.id = p.fonte_dado_id
   AND f.nome = 'Filiados PCdoB - Durval'
   AND p.excluido_em IS NULL;

-- 4) Conferir após o UPDATE (esperado: 0 ativos restantes)
SELECT COUNT(*) AS restantes_ativos
  FROM cadastro.pessoa p
  JOIN etl.fonte_dado f ON f.id = p.fonte_dado_id
 WHERE f.nome = 'Filiados PCdoB - Durval'
   AND p.excluido_em IS NULL;

-- COMMIT;
-- ROLLBACK;
