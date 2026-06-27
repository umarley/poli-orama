from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Base explicita para repositories orientados a uma sessao/transacao."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
