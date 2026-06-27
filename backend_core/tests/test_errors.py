from fastapi.testclient import TestClient

from app.core.errors import ResourceNotFoundError
from app.main import app


def test_validation_error_uses_standard_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/tenants?page=0")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"] == "Dados da requisicao invalidos."
    assert isinstance(body["details"], list)
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_business_error_uses_standard_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/tenants?order_by=campo_inexistente")

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_order_field"
    assert "allowed" in response.json()["details"]


def test_not_found_uses_standard_contract() -> None:
    from app.tenants.router import get_tenant_service

    class MissingService:
        @staticmethod
        async def get_by_id(tenant_id: int) -> None:
            raise ResourceNotFoundError("Tenant", tenant_id)

    app.dependency_overrides[get_tenant_service] = MissingService
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/tenants/99")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["code"] == "resource_not_found"
    assert response.json()["details"] == {"identifier": 99}


def test_internal_error_hides_implementation_details() -> None:
    from app.tenants.router import get_tenant_service

    class BrokenService:
        @staticmethod
        async def get_by_id(tenant_id: int) -> None:
            raise RuntimeError(f"sensitive failure for {tenant_id}")

    app.dependency_overrides[get_tenant_service] = BrokenService
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/tenants/1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert response.json()["details"] is None
    assert "sensitive" not in response.text
