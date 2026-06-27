from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app


def test_health_returns_api_status_and_request_id() -> None:
    request_id = str(uuid4())

    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"] == request_id
    assert UUID(response.headers["X-Request-ID"])


def test_invalid_request_id_is_replaced() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "not-a-uuid"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "not-a-uuid"
    assert UUID(response.headers["X-Request-ID"])


def test_internal_health_skips_database_by_default() -> None:
    with TestClient(app) as client:
        response = client.get("/internal/health")

    assert response.status_code == 200
    assert response.json()["database"] == "not_checked"


def test_internal_health_checks_database_when_requested() -> None:
    with patch(
        "app.core.service.check_database_connection", new_callable=AsyncMock
    ) as database_check:
        with TestClient(app) as client:
            response = client.get("/internal/health?check_database=true")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    database_check.assert_awaited_once()


def test_internal_health_reports_database_failure() -> None:
    with patch(
        "app.core.service.check_database_connection",
        new_callable=AsyncMock,
        side_effect=SQLAlchemyError("connection failed"),
    ):
        with TestClient(app) as client:
            response = client.get("/internal/health?check_database=true")

    assert response.status_code == 503
    assert response.json()["code"] == "database_unavailable"


def test_local_frontend_origin_is_allowed_by_cors() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_openapi_has_domain_tags() -> None:
    with TestClient(app) as client:
        document = client.get("/openapi.json").json()

    tag_names = {tag["name"] for tag in document["tags"]}
    assert {
        "Infraestrutura",
        "Tenants",
        "Cadastro",
        "Territorio",
        "Metas",
        "Agenda",
        "Demandas",
        "Dashboard",
    } <= tag_names
