"""Endpoints exclusivos do perfil tesoureiro."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import RequestActor, get_db_session, require_any_profile
from app.mod_contrato.repository import ContractRepository
from app.mod_contrato.schemas import (
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    PersonOption,
)
from app.mod_contrato.service import ContractService

router = APIRouter(prefix="/contratos", tags=["Contratos"])
treasurer_actor = require_any_profile("tesoureiro")


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ContractService:
    return ContractService(ContractRepository(session))


@router.get("/pessoas", response_model=list[PersonOption])
async def search_people(
    actor: Annotated[RequestActor, Depends(treasurer_actor)],
    service: Annotated[ContractService, Depends(get_service)],
    q: str = Query(min_length=2, max_length=100),
) -> list[PersonOption]:
    return await service.people(actor, q)


@router.get("", response_model=list[ContractResponse])
async def list_contracts(
    actor: Annotated[RequestActor, Depends(treasurer_actor)],
    service: Annotated[ContractService, Depends(get_service)],
    q: str | None = Query(default=None, min_length=2, max_length=100),
    tipo_contratado: str | None = Query(default=None, pattern="^(pf|pj)$"),
    situacao: str | None = Query(default=None, pattern="^(rascunho|ativo|encerrado|cancelado)$"),
) -> list[ContractResponse]:
    return await service.list(actor, query=q, contractor_type=tipo_contratado, status=situacao)


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate,
    actor: Annotated[RequestActor, Depends(treasurer_actor)],
    service: Annotated[ContractService, Depends(get_service)],
) -> ContractResponse:
    return await service.create(actor, payload)


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    actor: Annotated[RequestActor, Depends(treasurer_actor)],
    service: Annotated[ContractService, Depends(get_service)],
    contract_id: int = Path(ge=1),
) -> ContractResponse:
    return await service.get(actor, contract_id)


@router.patch("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    payload: ContractUpdate,
    actor: Annotated[RequestActor, Depends(treasurer_actor)],
    service: Annotated[ContractService, Depends(get_service)],
    contract_id: int = Path(ge=1),
) -> ContractResponse:
    return await service.update(actor, contract_id, payload)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    actor: Annotated[RequestActor, Depends(treasurer_actor)],
    service: Annotated[ContractService, Depends(get_service)],
    contract_id: int = Path(ge=1),
) -> Response:
    await service.delete(actor, contract_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
