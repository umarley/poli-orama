"""Regra canonica de metas replicada no worker independente."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

ACTIVE_GOAL_STATUSES = ("ativa", "em_risco")
RANKING_ATTAINMENT_WEIGHT = Decimal("0.60")
RANKING_REGISTRATIONS_WEIGHT = Decimal("0.25")
RANKING_ENGAGEMENT_WEIGHT = Decimal("0.15")


def percentage(current: int, target: int) -> Decimal:
    if target <= 0:
        return Decimal("0.00")
    return (Decimal(current) * Decimal("100") / Decimal(target)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def risk_status(value: Decimal, threshold: Decimal) -> str:
    if value >= threshold:
        return "normal"
    if value >= threshold * Decimal("0.75"):
        return "atencao"
    if value >= threshold * Decimal("0.40"):
        return "risco"
    return "critico"


def alert_severity(status: str) -> str:
    return {
        "atencao": "baixa",
        "risco": "alta",
        "critico": "critica",
    }.get(status, "media")


def predictive_risk_score(
    *,
    current_percentage: Decimal,
    threshold: Decimal,
    tracking_percentages: list[Decimal],
    base_count: int,
    target: int,
    average_engagement: Decimal,
) -> tuple[Decimal, dict[str, Any]]:
    gap = max(Decimal("0"), threshold - current_percentage)
    coverage = percentage(base_count, target)
    stagnation = (
        len(tracking_percentages) >= 2
        and tracking_percentages[0] <= tracking_percentages[1]
    )
    score = min(
        Decimal("100"),
        gap * Decimal("1.15")
        + max(Decimal("0"), Decimal("70") - coverage) * Decimal("0.35")
        + max(
            Decimal("0"),
            Decimal("50") - average_engagement * Decimal("10"),
        )
        * Decimal("0.20")
        + (Decimal("15") if stagnation else Decimal("0")),
    ).quantize(Decimal("0.01"))
    return score, {
        "modelo": "heuristica_v1",
        "percentual_atual": current_percentage,
        "limiar": threshold,
        "cobertura_base": coverage,
        "engajamento_medio": average_engagement,
        "estagnada": stagnation,
    }
