"""Referencias minimas para tabelas externas aos modelos implementados.

Essas declaracoes nao criam tabelas nem representam entidades completas. Elas
permitem que o SQLAlchemy resolva ForeignKey durante flush e ordenacao do
metadata enquanto os respectivos dominios ainda nao possuem modelos ORM.
"""

from sqlalchemy import BigInteger, Column, Integer, SmallInteger, Table

from app.tenants.models import Base


def _reference_table(
    name: str, schema: str, column_type: type[BigInteger | Integer | SmallInteger]
) -> Table:
    return Table(
        name,
        Base.metadata,
        Column("id", column_type, primary_key=True),
        schema=schema,
    )


escolaridade = _reference_table("escolaridade", "cadastro", SmallInteger)
profissao = _reference_table("profissao", "cadastro", Integer)
religiao = _reference_table("religiao", "cadastro", SmallInteger)
partido = _reference_table("partido", "cadastro", SmallInteger)

arquivo = _reference_table("arquivo", "arquivo", BigInteger)
fonte_dado = _reference_table("fonte_dado", "etl", BigInteger)

municipio = _reference_table("municipio", "global", Integer)
bairro = _reference_table("bairro", "global", Integer)
zona_eleitoral = _reference_table("zona_eleitoral", "global", Integer)
secao_eleitoral = _reference_table("secao_eleitoral", "global", BigInteger)
local_votacao = _reference_table("local_votacao", "global", Integer)

territorio = _reference_table("territorio", "territorio", BigInteger)
