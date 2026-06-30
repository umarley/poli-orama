import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.errors import AppError
from app.tenants.repository import CommercialRepository
from app.tenants.schemas import (
    CheckoutCreate,
    CheckoutResponse,
    ContratacaoCreate,
    ContratacaoResponse,
    LeadCreate,
    LeadResponse,
    PaymentWebhook,
    PlanoResponse,
)
from app.tenants.service import CommercialService

router = APIRouter(prefix="/api/public", tags=["Publico"])


def get_commercial_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommercialService:
    return CommercialService(CommercialRepository(session), get_settings())


@router.get("/planos", response_model=list[PlanoResponse], summary="Lista planos comerciais ativos")
async def list_public_plans(
    service: Annotated[CommercialService, Depends(get_commercial_service)],
) -> list[PlanoResponse]:
    return await service.list_plans()


@router.post(
    "/leads",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra lead comercial",
)
async def create_lead(
    payload: LeadCreate,
    service: Annotated[CommercialService, Depends(get_commercial_service)],
) -> LeadResponse:
    return await service.create_lead(payload)


@router.post(
    "/contratacoes",
    response_model=ContratacaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria pre-cadastro de contratacao",
)
async def create_contract(
    payload: ContratacaoCreate,
    service: Annotated[CommercialService, Depends(get_commercial_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ContratacaoResponse:
    return await service.create_contratacao(payload, idempotency_key)


@router.post(
    "/checkout/session",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria sessao de checkout hospedado",
)
async def create_checkout(
    payload: CheckoutCreate,
    service: Annotated[CommercialService, Depends(get_commercial_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CheckoutResponse:
    return await service.create_checkout(payload, idempotency_key)


@router.post("/webhooks/payment", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def payment_webhook(
    request: Request,
    service: Annotated[CommercialService, Depends(get_commercial_service)],
    signature: Annotated[str | None, Header(alias="X-Webhook-Signature")] = None,
) -> None:
    body = await request.body()
    expected = hmac.new(
        get_settings().payment_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    supplied = (signature or "").removeprefix("sha256=")
    if not hmac.compare_digest(expected, supplied):
        raise AppError(
            status_code=401,
            code="invalid_webhook_signature",
            message="Assinatura do webhook invalida.",
        )
    try:
        event = PaymentWebhook.model_validate_json(body)
    except ValidationError as exc:
        raise AppError(
            status_code=422,
            code="invalid_webhook_payload",
            message="Payload do webhook invalido.",
            details=exc.errors(),
        ) from exc
    await service.process_webhook(
        event.event_id, event.event_type, event.contratacao_id, event.tenant_id
    )
