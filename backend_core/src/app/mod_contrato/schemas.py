"""Contratos HTTP do modulo de contratos."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ContractorType = Literal["pf", "pj"]
ContractStatus = Literal["rascunho", "ativo", "encerrado", "cancelado"]


class ContractSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def cnpj_is_valid(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 14 or digits == digits[0] * 14:
        return False

    def digit(base: str, weights: list[int]) -> str:
        total = sum(int(number) * weight for number, weight in zip(base, weights, strict=True))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first = digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = digit(digits[:12] + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digits[-2:] == first + second


class LegalEntityInput(ContractSchema):
    razao_social: str = Field(min_length=2, max_length=180)
    nome_fantasia: str | None = Field(default=None, max_length=180)
    cnpj: str = Field(min_length=14, max_length=18)
    telefone: str | None = Field(default=None, max_length=20)
    cep: str | None = Field(default=None, max_length=9)
    logradouro: str | None = Field(default=None, max_length=180)
    numero: str | None = Field(default=None, max_length=20)
    complemento: str | None = Field(default=None, max_length=120)
    bairro_texto: str | None = Field(default=None, max_length=150)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, value: str) -> str:
        normalized = re.sub(r"\D", "", value)
        if not cnpj_is_valid(normalized):
            raise ValueError("CNPJ invalido.")
        return normalized


class LegalEntityUpdate(ContractSchema):
    razao_social: str | None = Field(default=None, min_length=2, max_length=180)
    nome_fantasia: str | None = Field(default=None, max_length=180)
    telefone: str | None = Field(default=None, max_length=20)
    cep: str | None = Field(default=None, max_length=9)
    logradouro: str | None = Field(default=None, max_length=180)
    numero: str | None = Field(default=None, max_length=20)
    complemento: str | None = Field(default=None, max_length=120)
    bairro_texto: str | None = Field(default=None, max_length=150)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)


class ContractCreate(ContractSchema):
    campanha_eleicao_id: int | None = Field(default=None, ge=1)
    tipo_contratado: ContractorType
    pessoa_id: int | None = Field(default=None, ge=1)
    pessoa_juridica: LegalEntityInput | None = None
    funcao_cargo: str = Field(min_length=2, max_length=180)
    valor_parcela: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    quantidade_parcelas: Literal[1, 2, 3]
    data_inicio: date
    data_termino: date
    status: ContractStatus = "ativo"
    observacoes: str | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "ContractCreate":
        if self.data_termino <= self.data_inicio:
            raise ValueError("A data final deve ser posterior a data inicial.")
        if self.tipo_contratado == "pf":
            if self.pessoa_id is None or self.pessoa_juridica is not None:
                raise ValueError("Pessoa fisica deve referenciar um cadastro de pessoa existente.")
        elif self.pessoa_juridica is None or self.pessoa_id is not None:
            raise ValueError("Pessoa juridica exige os dados da empresa.")
        return self


class ContractUpdate(ContractSchema):
    funcao_cargo: str | None = Field(default=None, min_length=2, max_length=180)
    valor_parcela: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    quantidade_parcelas: Literal[1, 2, 3] | None = None
    data_inicio: date | None = None
    data_termino: date | None = None
    status: ContractStatus | None = None
    observacoes: str | None = None
    pessoa_juridica: LegalEntityUpdate | None = None


class ContractorResponse(ContractSchema):
    tipo: ContractorType
    id: int
    nome: str
    documento: str
    rg: str | None = None
    data_nascimento: date | None = None
    telefone: str | None = None
    cep: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    codigo_municipio_ibge: int | None = None
    cidade: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class ContractResponse(ContractSchema):
    id: int
    uuid_publico: UUID
    tenant_id: int
    campanha_eleicao_id: int
    tipo_contratado: ContractorType
    pessoa_id: int | None
    pessoa_juridica_id: int | None
    funcao_cargo: str
    valor_parcela: Decimal
    quantidade_parcelas: Literal[1, 2, 3]
    valor_total: Decimal
    data_inicio: date
    data_termino: date
    dias_trabalho: int
    valor_diaria: Decimal
    status: ContractStatus
    observacoes: str | None
    criado_em: datetime
    atualizado_em: datetime
    contratado: ContractorResponse


class PersonOption(ContractSchema):
    id: int
    nome: str
    cpf: str
    rg: str | None = None
    data_nascimento: date | None = None
    telefone: str | None = None
    cep: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    codigo_municipio_ibge: int | None = None
    cidade: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class ContractTotals(ContractSchema):
    valor_total: Decimal
    dias_trabalho: int
    valor_diaria: Decimal
