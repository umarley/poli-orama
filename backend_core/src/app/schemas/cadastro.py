"""Contratos de dados das entidades centrais de cadastro."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

Sexo = Literal["M", "F", "O", "N"]
TipoDocumento = Literal["cpf", "rg", "titulo_eleitor", "cnh", "passaporte", "outro"]
TipoContato = Literal["telefone", "celular", "whatsapp", "email", "outro"]
TipoEndereco = Literal["residencial", "eleitoral", "comercial", "temporario", "outro"]
SituacaoTitulo = Literal["regular", "suspenso", "cancelado", "desconhecido"]
TipoLideranca = Literal["coordenador_geral", "coordenador_territorial", "lider", "sublider"]


class CadastroSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class PessoaDocumentoBase(CadastroSchema):
    tipo_documento: TipoDocumento
    numero: str = Field(min_length=1, max_length=40)
    orgao_emissor: str | None = Field(default=None, max_length=40)
    uf_emissor: str | None = Field(default=None, min_length=2, max_length=2)
    data_emissao: date | None = None

    @field_validator("numero")
    @classmethod
    def normalize_document_number(cls, value: str) -> str:
        return re.sub(r"\W", "", value).upper()

    @model_validator(mode="after")
    def validate_cpf(self) -> "PessoaDocumentoBase":
        if self.tipo_documento == "cpf" and not _cpf_is_valid(self.numero):
            raise ValueError("CPF invalido.")
        return self


class PessoaDocumentoCreate(PessoaDocumentoBase):
    pass


class PessoaDocumentoUpdate(CadastroSchema):
    numero: str | None = Field(default=None, min_length=1, max_length=40)
    orgao_emissor: str | None = Field(default=None, max_length=40)
    uf_emissor: str | None = Field(default=None, min_length=2, max_length=2)
    data_emissao: date | None = None


class PessoaDocumentoResponse(PessoaDocumentoBase):
    id: int
    tenant_id: int
    pessoa_id: int
    criado_em: datetime


class PessoaContatoBase(CadastroSchema):
    tipo_contato: TipoContato
    valor: str = Field(min_length=1, max_length=180)
    principal: bool = False
    verificado: bool = False
    observacao: str | None = Field(default=None, max_length=255)

    @field_validator("valor")
    @classmethod
    def validate_contact(cls, value: str, info: ValidationInfo) -> str:
        contact_type = info.data.get("tipo_contato")
        normalized = value.strip()
        if contact_type == "email":
            normalized = normalized.lower()
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
                raise ValueError("E-mail invalido.")
        elif contact_type in {"telefone", "celular", "whatsapp"}:
            normalized = re.sub(r"\D", "", normalized)
            if not re.fullmatch(r"(?:55)?\d{10,11}", normalized):
                raise ValueError("Telefone invalido; informe DDD e numero.")
        return normalized


class PessoaContatoCreate(PessoaContatoBase):
    pass


class PessoaContatoUpdate(CadastroSchema):
    valor: str | None = Field(default=None, min_length=1, max_length=180)
    principal: bool | None = None
    verificado: bool | None = None
    observacao: str | None = Field(default=None, max_length=255)


class PessoaContatoResponse(PessoaContatoBase):
    id: int
    tenant_id: int
    pessoa_id: int
    criado_em: datetime


class EnderecoBase(CadastroSchema):
    municipio_id: int | None = Field(default=None, ge=1)
    bairro_id: int | None = Field(default=None, ge=1)
    bairro_texto: str | None = Field(default=None, max_length=150)
    logradouro: str | None = Field(default=None, max_length=180)
    numero: str | None = Field(default=None, max_length=20)
    complemento: str | None = Field(default=None, max_length=120)
    cep: str | None = Field(default=None, max_length=9)
    ponto_referencia: str | None = Field(default=None, max_length=180)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)


class EnderecoCreate(EnderecoBase):
    pass


class EnderecoUpdate(CadastroSchema):
    municipio_id: int | None = Field(default=None, ge=1)
    bairro_id: int | None = Field(default=None, ge=1)
    bairro_texto: str | None = Field(default=None, max_length=150)
    logradouro: str | None = Field(default=None, max_length=180)
    numero: str | None = Field(default=None, max_length=20)
    complemento: str | None = Field(default=None, max_length=120)
    cep: str | None = Field(default=None, max_length=9)
    ponto_referencia: str | None = Field(default=None, max_length=180)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)


class EnderecoResponse(EnderecoBase):
    id: int
    tenant_id: int
    geocodificado: bool
    criado_em: datetime
    atualizado_em: datetime


class PessoaEnderecoCreate(CadastroSchema):
    endereco: EnderecoCreate
    tipo: TipoEndereco = "residencial"
    principal: bool = False


class PessoaEnderecoUpdate(CadastroSchema):
    tipo: TipoEndereco | None = None
    principal: bool | None = None
    endereco: EnderecoUpdate | None = None


class PessoaEnderecoResponse(CadastroSchema):
    id: int
    tenant_id: int
    pessoa_id: int
    endereco_id: int
    tipo: TipoEndereco
    principal: bool
    endereco: EnderecoResponse


class EleitorBase(CadastroSchema):
    titulo_eleitor: str | None = Field(default=None, max_length=20)
    zona_eleitoral_id: int | None = Field(default=None, ge=1)
    secao_eleitoral_id: int | None = Field(default=None, ge=1)
    local_votacao_id: int | None = Field(default=None, ge=1)
    municipio_voto_id: int | None = Field(default=None, ge=1)
    situacao_titulo: SituacaoTitulo | None = "regular"

    @field_validator("titulo_eleitor")
    @classmethod
    def normalize_voter_title(cls, value: str | None) -> str | None:
        return re.sub(r"\D", "", value) if value else value


class EleitorCreate(EleitorBase):
    pass


class EleitorUpdate(CadastroSchema):
    titulo_eleitor: str | None = Field(default=None, max_length=20)
    zona_eleitoral_id: int | None = Field(default=None, ge=1)
    secao_eleitoral_id: int | None = Field(default=None, ge=1)
    local_votacao_id: int | None = Field(default=None, ge=1)
    municipio_voto_id: int | None = Field(default=None, ge=1)
    situacao_titulo: SituacaoTitulo | None = None


class EleitorResponse(EleitorBase):
    id: int
    tenant_id: int
    pessoa_id: int
    criado_em: datetime
    atualizado_em: datetime


class LiderancaBase(CadastroSchema):
    tipo_lideranca: TipoLideranca = "lider"
    coordenador_id: int | None = Field(default=None, ge=1)
    meta_votos: int | None = Field(default=None, ge=0)
    apelido_campanha: str | None = Field(default=None, max_length=120)
    ativo: bool = True


class LiderancaCreate(LiderancaBase):
    pass


class LiderancaUpdate(CadastroSchema):
    tipo_lideranca: TipoLideranca | None = None
    coordenador_id: int | None = Field(default=None, ge=1)
    meta_votos: int | None = Field(default=None, ge=0)
    apelido_campanha: str | None = Field(default=None, max_length=120)
    ativo: bool | None = None


class LiderancaResponse(LiderancaBase):
    id: int
    tenant_id: int
    pessoa_id: int
    criado_em: datetime
    atualizado_em: datetime


class PessoaBase(CadastroSchema):
    nome_completo: str = Field(min_length=2, max_length=180)
    nome_social: str | None = Field(default=None, max_length=180)
    apelido: str | None = Field(default=None, max_length=120)
    sexo: Sexo | None = None
    data_nascimento: date | None = None
    estado_civil: int | None = Field(default=None, ge=1)
    escolaridade_id: int | None = Field(default=None, ge=1)
    profissao_id: int | None = Field(default=None, ge=1)
    religiao_id: int | None = Field(default=None, ge=1)
    observacoes: str | None = None


class PessoaCreate(PessoaBase):
    documentos: list[PessoaDocumentoCreate] = Field(default_factory=list)
    contatos: list[PessoaContatoCreate] = Field(default_factory=list)
    enderecos: list[PessoaEnderecoCreate] = Field(default_factory=list)
    eleitor: EleitorCreate | None = None
    lideranca: LiderancaCreate | None = None

    @model_validator(mode="after")
    def validate_principal_records(self) -> "PessoaCreate":
        principal_contacts = [
            contact.tipo_contato for contact in self.contatos if contact.principal
        ]
        if len(principal_contacts) != len(set(principal_contacts)):
            raise ValueError("Aceito apenas um contato principal de cada tipo.")
        principal_addresses = [address.tipo for address in self.enderecos if address.principal]
        if len(principal_addresses) != len(set(principal_addresses)):
            raise ValueError("Aceito apenas um endereco principal de cada tipo.")
        return self


class PessoaUpdate(CadastroSchema):
    nome_completo: str | None = Field(default=None, min_length=2, max_length=180)
    nome_social: str | None = Field(default=None, max_length=180)
    apelido: str | None = Field(default=None, max_length=120)
    sexo: Sexo | None = None
    data_nascimento: date | None = None
    estado_civil: int | None = Field(default=None, ge=1)
    escolaridade_id: int | None = Field(default=None, ge=1)
    profissao_id: int | None = Field(default=None, ge=1)
    religiao_id: int | None = Field(default=None, ge=1)
    observacoes: str | None = None
    ativo: bool | None = None


class PessoaResponse(PessoaBase):
    id: int
    uuid_publico: UUID
    tenant_id: int
    nivel_engajamento: int | None
    score_confiabilidade: Decimal | None
    completude_cadastral: Decimal | None
    ativo: bool
    criado_por: int | None
    atualizado_por: int | None
    criado_em: datetime
    atualizado_em: datetime
    excluido_em: datetime | None
    documentos: list[PessoaDocumentoResponse] = Field(default_factory=list)
    contatos: list[PessoaContatoResponse] = Field(default_factory=list)
    enderecos: list[PessoaEnderecoResponse] = Field(default_factory=list)
    eleitor: EleitorResponse | None = None
    lideranca: LiderancaResponse | None = None


def _cpf_is_valid(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    for size in (9, 10):
        total = sum(
            int(digit) * weight
            for digit, weight in zip(digits[:size], range(size + 1, 1, -1), strict=True)
        )
        check = (total * 10) % 11
        if check == 10:
            check = 0
        if check != int(digits[size]):
            return False
    return True
