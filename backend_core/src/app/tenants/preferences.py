MAXIMO_ATENDIMENTOS_SIMULTANEOS_PADRAO = 10
MAXIMO_ATENDIMENTOS_SIMULTANEOS_MINIMO = 1
MAXIMO_ATENDIMENTOS_SIMULTANEOS_MAXIMO = 50
PREFERENCIA_FILA_ATENDIMENTO = "maximo_atendimentos_simultaneos"


def parse_maximo_atendimentos_simultaneos(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def maximo_atendimentos_simultaneos(preferencias: dict[str, object] | None) -> int:
    parsed = parse_maximo_atendimentos_simultaneos(
        (preferencias or {}).get(PREFERENCIA_FILA_ATENDIMENTO)
    )
    if parsed is None:
        return MAXIMO_ATENDIMENTOS_SIMULTANEOS_PADRAO
    return max(
        MAXIMO_ATENDIMENTOS_SIMULTANEOS_MINIMO,
        min(parsed, MAXIMO_ATENDIMENTOS_SIMULTANEOS_MAXIMO),
    )
