"""OAuth 2.0 e sincronizacao incremental com Google Calendar API v3."""

import base64
import hashlib
import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from urllib.parse import quote, urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi.encoders import jsonable_encoder

from app.audit.service import AuditService
from app.auth.access import RequestActor
from app.core.config import Settings, get_settings
from app.core.errors import BusinessRuleError
from app.mod_agenda.repository import AgendaRepository
from app.mod_agenda.schemas import (
    GoogleCalendarItem,
    GoogleCalendarLinkInput,
    GoogleCalendarLinkResponse,
    GoogleOAuthStartResponse,
    GoogleSyncResponse,
)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_API_URL = "https://www.googleapis.com/calendar/v3"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_SCOPES = (
    "openid email https://www.googleapis.com/auth/calendar.calendarlist.readonly "
    "https://www.googleapis.com/auth/calendar.events"
)


class GoogleCalendarError(BusinessRuleError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message, code="google_calendar_error")
        self.google_status = status


class TokenCipher:
    def __init__(self, secret: str) -> None:
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self.fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise GoogleCalendarError("Nao foi possivel ler as credenciais do Google.") from exc


class GoogleCalendarClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.http = http or httpx.AsyncClient(timeout=30)

    def ensure_configured(self) -> None:
        if (
            not self.settings.google_calendar_client_id
            or not self.settings.google_calendar_client_secret
        ):
            raise GoogleCalendarError("A integracao com Google Agenda ainda nao foi configurada.")

    async def exchange_code(self, code: str, verifier: str) -> dict[str, Any]:
        self.ensure_configured()
        response = await self.http.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": self.settings.google_calendar_client_id,
                "client_secret": self.settings.google_calendar_client_secret,
                "redirect_uri": self.settings.google_calendar_redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
        )
        return self._json(response, "Nao foi possivel concluir a autorizacao do Google.")

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        response = await self.http.post(
            GOOGLE_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": self.settings.google_calendar_client_id,
                "client_secret": self.settings.google_calendar_client_secret,
                "grant_type": "refresh_token",
            },
        )
        return self._json(response, "A autorizacao do Google expirou ou foi revogada.")

    async def get_json(
        self, path: str, access_token: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        response = await self.http.get(
            path if path.startswith("https://") else f"{GOOGLE_API_URL}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        return self._json(response, "Falha ao consultar o Google Agenda.")

    async def send_json(
        self,
        method: str,
        path: str,
        access_token: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self.http.request(
            method,
            f"{GOOGLE_API_URL}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )
        if response.status_code == 404 and method == "DELETE":
            return {}
        return self._json(response, "Falha ao atualizar o Google Agenda.")

    @staticmethod
    def _json(response: httpx.Response, fallback: str) -> dict[str, Any]:
        if response.is_success:
            return response.json() if response.content else {}
        try:
            detail = response.json().get("error", {})
            if isinstance(detail, dict):
                message = detail.get("message") or detail.get("error_description")
            else:
                message = str(detail)
        except ValueError:
            message = None
        raise GoogleCalendarError(str(message or fallback), response.status_code)


class GoogleCalendarService:
    def __init__(
        self,
        repository: AgendaRepository,
        settings: Settings | None = None,
        client: GoogleCalendarClient | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self.client = client or GoogleCalendarClient(self.settings)
        self.cipher = TokenCipher(self.settings.google_calendar_encryption_key)

    async def start_oauth(self, actor: RequestActor) -> GoogleOAuthStartResponse:
        self.client.ensure_configured()
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        await self.repository.create_oauth_state(
            actor.tenant_id,
            actor.user_id,
            hashlib.sha256(state.encode()).hexdigest(),
            self.cipher.encrypt(verifier),
            datetime.now(UTC) + timedelta(minutes=10),
        )
        await self.repository.commit()
        params = {
            "client_id": self.settings.google_calendar_client_id,
            "redirect_uri": self.settings.google_calendar_redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_SCOPES,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return GoogleOAuthStartResponse(authorization_url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")

    async def finish_oauth(self, state: str, code: str) -> None:
        oauth_state = await self.repository.consume_oauth_state(
            hashlib.sha256(state.encode()).hexdigest()
        )
        if oauth_state is None:
            raise GoogleCalendarError("A autorizacao expirou ou ja foi utilizada.")
        tenant_id = int(oauth_state["tenant_id"])
        await self.repository.set_tenant_context(tenant_id)
        tokens = await self.client.exchange_code(
            code, self.cipher.decrypt(oauth_state["code_verifier_criptografado"])
        )
        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")
        if not refresh_token or not access_token:
            raise GoogleCalendarError("O Google nao retornou credenciais para acesso offline.")
        userinfo = await self.client.get_json(GOOGLE_USERINFO_URL, access_token)
        owner = await self.repository.google_subject_user(tenant_id, str(userinfo["sub"]))
        if owner is not None and owner != int(oauth_state["usuario_id"]):
            raise GoogleCalendarError(
                "Esta conta Google ja esta conectada a outro usuario deste tenant."
            )
        expires_at = datetime.now(UTC) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
        await self.repository.upsert_google_account(
            tenant_id,
            int(oauth_state["usuario_id"]),
            str(userinfo["sub"]),
            userinfo.get("email"),
            self.cipher.encrypt(refresh_token),
            self.cipher.encrypt(access_token),
            expires_at,
            str(tokens.get("scope", GOOGLE_SCOPES)),
        )
        await AuditService(self.repository.session).record(
            action="integrar",
            tenant_id=tenant_id,
            user_id=int(oauth_state["usuario_id"]),
            schema_name="agenda",
            table_name="google_conta_usuario",
            record_id=int(oauth_state["usuario_id"]),
            after={"email": userinfo.get("email"), "escopos": tokens.get("scope")},
        )
        await self.repository.commit()

    async def calendars(self, actor: RequestActor) -> list[GoogleCalendarItem]:
        account = await self._account(actor.tenant_id, actor.user_id)
        items = await self._calendar_items(account)
        await self.repository.commit()
        return items

    async def _calendar_items(self, account: dict[str, Any]) -> list[GoogleCalendarItem]:
        token = await self._access_token(account)
        items: list[GoogleCalendarItem] = []
        page_token: str | None = None
        while True:
            data = await self.client.get_json(
                "/users/me/calendarList",
                token,
                params={"minAccessRole": "writer", "maxResults": 250, "pageToken": page_token},
            )
            items.extend(
                GoogleCalendarItem(
                    id=str(item["id"]),
                    nome=str(item.get("summaryOverride") or item.get("summary") or item["id"]),
                    principal=bool(item.get("primary")),
                    acesso=str(item.get("accessRole", "writer")),
                )
                for item in data.get("items", [])
                if not item.get("deleted")
            )
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return items

    async def link(
        self, actor: RequestActor, calendar_id: int, payload: GoogleCalendarLinkInput
    ) -> GoogleCalendarLinkResponse:
        account = await self._account(actor.tenant_id, actor.user_id)
        current = await self.repository.google_integration(actor.tenant_id, calendar_id)
        available = {item.id: item for item in await self._calendar_items(account)}
        selected = available.get(payload.google_calendar_id)
        if selected is None:
            raise GoogleCalendarError(
                "A agenda Google selecionada nao esta disponivel para escrita."
            )
        item = await self.repository.link_google_calendar(
            actor.tenant_id,
            calendar_id,
            int(account["id"]),
            actor.user_id,
            selected.id,
            selected.nome,
            payload.direcao,
        )
        await AuditService(self.repository.session).record(
            action="integrar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="agenda",
            table_name="google_integracao_agenda",
            record_id=int(item["id"]),
            before=self._integration_audit(current),
            after=jsonable_encoder(item),
        )
        await self.repository.commit()
        return GoogleCalendarLinkResponse.model_validate(item)

    async def unlink(self, actor: RequestActor, calendar_id: int) -> None:
        current = await self.repository.google_integration(actor.tenant_id, calendar_id)
        await self.repository.unlink_google_calendar(actor.tenant_id, calendar_id)
        if current:
            await AuditService(self.repository.session).record(
                action="excluir",
                tenant_id=actor.tenant_id,
                user_id=actor.user_id,
                schema_name="agenda",
                table_name="google_integracao_agenda",
                record_id=int(current["id"]),
                before=self._integration_audit(current),
            )
        await self.repository.commit()

    async def sync(self, actor: RequestActor, calendar_id: int) -> GoogleSyncResponse:
        integration = await self.repository.google_integration(actor.tenant_id, calendar_id)
        if integration is None:
            raise GoogleCalendarError("Esta agenda nao possui vinculo ativo com o Google.")
        token = await self._access_token(integration)
        result = GoogleSyncResponse()
        try:
            if integration["direcao"] in {"google_sistema", "bidirecional"}:
                await self._pull(integration, token, result)
            if integration["direcao"] in {"sistema_google", "bidirecional"}:
                await self._push(integration, token, result)
            await self.repository.finish_google_sync(
                int(integration["id"]), integration.get("sync_token")
            )
            await AuditService(self.repository.session).record(
                action="sincronizar",
                tenant_id=actor.tenant_id,
                user_id=actor.user_id,
                schema_name="agenda",
                table_name="google_integracao_agenda",
                record_id=int(integration["id"]),
                after=result.model_dump(),
            )
            await self.repository.commit()
        except GoogleCalendarError as exc:
            await self.repository.finish_google_sync(int(integration["id"]), None, str(exc))
            await self.repository.commit()
            raise
        return result

    async def _pull(
        self, integration: dict[str, Any], token: str, result: GoogleSyncResponse
    ) -> None:
        page_token: str | None = None
        sync_token = integration.get("sync_token")
        while True:
            params: dict[str, Any] = {
                "showDeleted": "true",
                "singleEvents": "true",
                "maxResults": 2500,
                "pageToken": page_token,
            }
            if sync_token:
                params["syncToken"] = sync_token
            try:
                data = await self.client.get_json(
                    f"/calendars/{quote(str(integration['google_calendar_id']), safe='')}/events",
                    token,
                    params=params,
                )
            except GoogleCalendarError as exc:
                if getattr(exc, "google_status", None) == 410 and sync_token:
                    integration["sync_token"] = None
                    return await self._pull(integration, token, result)
                raise
            for google_event in data.get("items", []):
                await self._import_one(integration, google_event, result)
            page_token = data.get("nextPageToken")
            if not page_token:
                integration["sync_token"] = data.get("nextSyncToken")
                break

    async def _import_one(
        self, integration: dict[str, Any], item: dict[str, Any], result: GoogleSyncResponse
    ) -> None:
        google_id = str(item["id"])
        if item.get("visibility") == "private" and integration["agenda_visibilidade"] == "publica":
            result.erros.append(
                f"Evento privado {google_id} nao importado para uma agenda publica."
            )
            return
        link = await self.repository.google_event_link(int(integration["id"]), google_id)
        private = item.get("extendedProperties", {}).get("private", {})
        local_id = private.get("poliorama_evento_id")
        if (
            link is None
            and local_id
            and private.get("poliorama_tenant_id") == str(integration["tenant_id"])
        ):
            local = await self.repository.get_event(int(integration["tenant_id"]), int(local_id))
            if local and int(local["agenda_id"]) == int(integration["agenda_id"]):
                link = {"evento_id": int(local_id), "google_atualizado_em": None}
        cancelled = item.get("status") == "cancelled"
        if cancelled and link is None:
            return
        google_updated = self._parse_datetime(item.get("updated"))
        if cancelled:
            assert link is not None
            event_id = int(link["evento_id"])
            await self.repository.cancel_imported_event(int(integration["tenant_id"]), event_id)
            await self.repository.upsert_google_event_link(
                int(integration["tenant_id"]),
                int(integration["id"]),
                event_id,
                google_id,
                item.get("etag"),
                google_updated,
                datetime.now(UTC),
            )
            result.atualizados += 1
            return
        if not integration.get("pessoa_id"):
            result.erros.append(
                f"Evento {google_id} nao importado: usuario Google sem pessoa vinculada."
            )
            return
        start = self._google_datetime(item.get("start", {}))
        if start is None:
            return
        end = self._google_datetime(item.get("end", {}))
        if link is None:
            event_id = await self.repository.import_google_event(
                int(integration["tenant_id"]),
                int(integration["agenda_id"]),
                int(integration["pessoa_id"]),
                str(item.get("summary") or "Compromisso do Google"),
                item.get("description"),
                start,
                end,
                item.get("location"),
            )
            result.importados += 1
        else:
            event_id = int(link["evento_id"])
            if (
                google_updated
                and link.get("google_atualizado_em")
                and google_updated <= link["google_atualizado_em"]
            ):
                return
            await self.repository.update_imported_event(
                int(integration["tenant_id"]),
                event_id,
                str(item.get("summary") or "Compromisso do Google"),
                item.get("description"),
                start,
                end,
                item.get("location"),
                cancelled,
            )
            result.atualizados += 1
        await self.repository.upsert_google_event_link(
            int(integration["tenant_id"]),
            int(integration["id"]),
            event_id,
            google_id,
            item.get("etag"),
            google_updated,
            datetime.now(UTC),
        )

    async def _push(
        self, integration: dict[str, Any], token: str, result: GoogleSyncResponse
    ) -> None:
        events = await self.repository.events_for_google_sync(
            int(integration["tenant_id"]), int(integration["agenda_id"])
        )
        base_path = f"/calendars/{quote(str(integration['google_calendar_id']), safe='')}/events"
        for event in events:
            google_id = event.get("google_event_id")
            if (
                google_id
                and event.get("sistema_atualizado_em")
                and event["atualizado_em"] <= event["sistema_atualizado_em"]
            ):
                continue
            if google_id and (
                event.get("excluido_em") or event.get("status_evento_codigo") == "cancelado"
            ):
                await self.client.send_json(
                    "DELETE", f"{base_path}/{quote(str(google_id), safe='')}", token
                )
                await self.repository.mark_google_event_deleted(
                    int(integration["id"]), int(event["id"])
                )
                result.removidos += 1
                continue
            payload = self._event_payload(event)
            remote = await self.client.send_json(
                "PUT" if google_id else "POST",
                f"{base_path}/{quote(str(google_id), safe='')}" if google_id else base_path,
                token,
                payload,
            )
            await self.repository.upsert_google_event_link(
                int(integration["tenant_id"]),
                int(integration["id"]),
                int(event["id"]),
                str(remote["id"]),
                remote.get("etag"),
                self._parse_datetime(remote.get("updated")),
                event["atualizado_em"],
            )
            result.enviados += 1

    async def _account(self, tenant_id: int, user_id: int) -> dict[str, Any]:
        account = await self.repository.google_account(tenant_id, user_id)
        if account is None:
            raise GoogleCalendarError("Conecte sua conta Google antes de selecionar uma agenda.")
        return account

    async def _access_token(self, account: dict[str, Any]) -> str:
        expires_at = account.get("access_token_expira_em")
        if (
            account.get("access_token_criptografado")
            and expires_at
            and expires_at > datetime.now(UTC) + timedelta(minutes=1)
        ):
            return self.cipher.decrypt(account["access_token_criptografado"])
        refreshed = await self.client.refresh(
            self.cipher.decrypt(account["refresh_token_criptografado"])
        )
        token = str(refreshed["access_token"])
        new_expiry = datetime.now(UTC) + timedelta(seconds=int(refreshed.get("expires_in", 3600)))
        await self.repository.update_google_access_token(
            int(account.get("google_conta_id") or account["id"]),
            self.cipher.encrypt(token),
            new_expiry,
        )
        account["access_token_expira_em"] = new_expiry
        account["access_token_criptografado"] = self.cipher.encrypt(token)
        return token

    @staticmethod
    def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "summary": event["titulo"],
            "description": event.get("descricao") or "",
            "location": event.get("local_nome") or "",
            "start": {"dateTime": event["data_inicio"].isoformat()},
            "end": {
                "dateTime": (
                    event.get("data_fim") or event["data_inicio"] + timedelta(hours=1)
                ).isoformat()
            },
            "extendedProperties": {
                "private": {
                    "poliorama_evento_id": str(event["id"]),
                    "poliorama_tenant_id": str(event["tenant_id"]),
                }
            },
        }
        return payload

    @staticmethod
    def _integration_audit(value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        allowed = (
            "id",
            "agenda_id",
            "google_calendar_id",
            "google_calendar_nome",
            "direcao",
            "status",
            "ultima_sincronizacao_em",
            "ultimo_erro",
        )
        return cast(dict[str, Any], jsonable_encoder({key: value.get(key) for key in allowed}))

    @classmethod
    def _google_datetime(cls, value: dict[str, Any]) -> datetime | None:
        if value.get("dateTime"):
            return cls._parse_datetime(value["dateTime"])
        if value.get("date"):
            return datetime.combine(date.fromisoformat(value["date"]), datetime.min.time(), UTC)
        return None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
