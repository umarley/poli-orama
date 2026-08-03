"""Contexto de cadastro originado no app mobile de lideranca."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MobileLeaderContext:
    cadastrado_por_lideranca_id: int
    origem_cadastro: str = "lider_mobile"
    hierarquia_origem: str = "lider_mobile"
    fonte_dado_id: int | None = None
