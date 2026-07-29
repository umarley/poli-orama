from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class User(Base):
    __tablename__ = "usuario"
    __table_args__ = {"schema": "auth"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid_publico: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    usuario_plataforma_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id", ondelete="RESTRICT")
    )
    pessoa_id: Mapped[int | None] = mapped_column(BigInteger)
    nome: Mapped[str] = mapped_column(String(180))
    email: Mapped[str] = mapped_column(String(254))
    hash_senha: Mapped[str] = mapped_column(Text)
    telefone: Mapped[str | None] = mapped_column(String(20))
    mfa_habilitado: Mapped[bool] = mapped_column(Boolean)
    mfa_segredo: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    ultimo_login_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tentativas_login: Mapped[int] = mapped_column(SmallInteger)
    senha_alterada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deve_alterar_senha: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AccessProfile(Base):
    __tablename__ = "perfil_acesso"
    __table_args__ = {"schema": "auth"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    nome: Mapped[str] = mapped_column(String(80))
    codigo: Mapped[str] = mapped_column(String(50))
    descricao: Mapped[str | None] = mapped_column(String(255))
    nivel: Mapped[int] = mapped_column(SmallInteger)
    sistema: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Permission(Base):
    __tablename__ = "permissao"
    __table_args__ = {"schema": "auth"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(100), unique=True)
    modulo: Mapped[str] = mapped_column(String(60))
    acao: Mapped[str] = mapped_column(String(30))
    descricao: Mapped[str | None] = mapped_column(String(255))


class ProfilePermission(Base):
    __tablename__ = "perfil_permissao"
    __table_args__ = {"schema": "auth"}

    perfil_acesso_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("auth.perfil_acesso.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permissao_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("auth.permissao.id", ondelete="CASCADE"),
        primary_key=True,
    )
    concedida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserProfile(Base):
    __tablename__ = "usuario_perfil"
    __table_args__ = {"schema": "auth"}

    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id", ondelete="CASCADE"), primary_key=True
    )
    perfil_acesso_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("auth.perfil_acesso.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    atribuido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserSession(Base):
    __tablename__ = "sessao_usuario"
    __table_args__ = {"schema": "auth"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(Text)
    dispositivo: Mapped[str | None] = mapped_column(String(180))
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_origem: Mapped[str | None] = mapped_column(INET)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultimo_uso_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TerritorialAccessPolicy(Base):
    __tablename__ = "politica_acesso_territorial"
    __table_args__ = {"schema": "auth"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id", ondelete="CASCADE")
    )
    tipo_escopo: Mapped[str] = mapped_column(String(30))
    codigo_uf_ibge: Mapped[int | None] = mapped_column(SmallInteger)
    codigo_municipio_ibge: Mapped[int | None] = mapped_column(Integer)
    bairro_id: Mapped[int | None] = mapped_column(Integer)
    zona_eleitoral_id: Mapped[int | None] = mapped_column(Integer)
    secao_eleitoral_id: Mapped[int | None] = mapped_column(BigInteger)
    territorio_id: Mapped[int | None] = mapped_column(BigInteger)
    pode_administrar: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
