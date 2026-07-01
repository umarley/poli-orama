"""Configuracao compartilhada dos testes de integracao."""

import os

# A API e as conexoes administrativas dos testes devem apontar para o mesmo banco.
# A atribuicao ocorre antes da coleta dos modulos que importam app.core.database.
if test_database_url := os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = test_database_url
