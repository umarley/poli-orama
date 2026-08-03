BEGIN;

-- Contas tecnicas usadas para aplicar o contexto RLS de um gestor SaaS nao
-- pertencem ao quadro de usuarios do tenant e nao devem persistir perfis.
-- O backend deriva o acesso da identidade global vinculada.
DELETE FROM auth.usuario_perfil up
USING auth.usuario u
WHERE u.id = up.usuario_id
  AND u.usuario_plataforma_id IS NOT NULL;

COMMIT;
