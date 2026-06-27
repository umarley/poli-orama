from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class ListParams:
    page: int = 1
    page_size: int = 20
    order_by: str = "id"
    direction: SortDirection = SortDirection.ASC
    query: str | None = None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def list_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    order_by: Annotated[str, Query(min_length=1, max_length=50)] = "id",
    direction: Annotated[SortDirection, Query()] = SortDirection.ASC,
    query: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> ListParams:
    return ListParams(
        page=page,
        page_size=page_size,
        order_by=order_by,
        direction=direction,
        query=query,
    )


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)

    @classmethod
    def create(cls, items: list[T], total: int, params: ListParams) -> "Page[T]":
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )
