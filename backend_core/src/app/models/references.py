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
eleicao = _reference_table("eleicao", "eleicao", BigInteger)
