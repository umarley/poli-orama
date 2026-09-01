"""Regra SQL central de visibilidade de agendas e dos recursos vinculados."""


def calendar_view_clause(calendar_alias: str = "a", user_parameter: str = "user_id") -> str:
    """Permite agenda publica ou agenda restrita compartilhada com o usuario."""
    return (
        f"({calendar_alias}.visibilidade = 'publica' OR EXISTS ("
        "SELECT 1 FROM agenda.agenda_usuario au "
        f"WHERE au.agenda_id = {calendar_alias}.id "
        f"AND au.tenant_id = {calendar_alias}.tenant_id "
        f"AND au.usuario_id = :{user_parameter} AND au.pode_visualizar))"
    )
