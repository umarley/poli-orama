"""Modelos SQLAlchemy compartilhados pela aplicacao."""

# Registra primeiro as tabelas referenciadas por ForeignKey nos demais modelos.
from app.auth import models as _auth_models  # noqa: F401
from app.models import references as _references  # noqa: F401
from app.models.cadastro import (
    Eleitor,
    Endereco,
    Lideranca,
    Pessoa,
    PessoaContato,
    PessoaDocumento,
    PessoaEndereco,
)
from app.models.cadastro_relacoes import (
    Comunidade,
    HierarquiaLideranca,
    Indicacao,
    NucleoFamiliar,
    PessoaComplementoPolitico,
    PessoaComunidade,
    PessoaMerge,
    PessoaNucleoFamiliar,
    PessoaPessoaTipo,
    PessoaRedeSocial,
    PessoaTag,
    PessoaTipo,
    RelacionamentoPessoa,
    SuspeitaDuplicidade,
    Tag,
    ValidacaoCadastro,
)

__all__ = [
    "Eleitor",
    "Endereco",
    "Comunidade",
    "HierarquiaLideranca",
    "Indicacao",
    "Lideranca",
    "NucleoFamiliar",
    "Pessoa",
    "PessoaComplementoPolitico",
    "PessoaComunidade",
    "PessoaContato",
    "PessoaDocumento",
    "PessoaEndereco",
    "PessoaNucleoFamiliar",
    "PessoaMerge",
    "PessoaPessoaTipo",
    "PessoaRedeSocial",
    "PessoaTag",
    "PessoaTipo",
    "RelacionamentoPessoa",
    "SuspeitaDuplicidade",
    "Tag",
    "ValidacaoCadastro",
]
