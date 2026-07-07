"""Adapters dos storages local, AWS S3 e SeaweedFS."""

from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import anyio
import httpx

from app.core.config import Settings
from app.core.errors import BusinessRuleError
from app.core.integracoes.aws_s3 import AwsS3Client
from app.core.integracoes.seaweed import SeaweedFilerClient


@dataclass(frozen=True, slots=True)
class StoredObject:
    provider: str
    bucket: str | None
    key: str
    stored_name: str


class StorageAdapter(Protocol):
    async def save(
        self, *, tenant_id: int, filename: str, extension: str, content: bytes
    ) -> StoredObject: ...

    async def read(self, *, bucket: str | None, key: str) -> bytes: ...

    async def delete(self, *, bucket: str | None, key: str) -> None: ...


def _object_key(tenant_id: int, extension: str) -> tuple[str, str]:
    suffix = f".{extension}" if extension else ""
    stored_name = f"{uuid4().hex}{suffix}"
    return f"{tenant_id}/{stored_name}", stored_name


class LocalStorage:
    provider = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    async def save(
        self, *, tenant_id: int, filename: str, extension: str, content: bytes
    ) -> StoredObject:
        del filename
        key, stored_name = _object_key(tenant_id, extension)
        path = self._resolve(key)
        await anyio.to_thread.run_sync(self._write, path, content)
        return StoredObject(self.provider, None, key, stored_name)

    async def read(self, *, bucket: str | None, key: str) -> bytes:
        del bucket
        path = self._resolve(key)
        if not path.is_file():
            raise BusinessRuleError(
                "Conteudo do arquivo nao foi encontrado no storage.",
                code="storage_object_not_found",
            )
        return await anyio.to_thread.run_sync(path.read_bytes)

    async def delete(self, *, bucket: str | None, key: str) -> None:
        del bucket
        path = self._resolve(key)
        await anyio.to_thread.run_sync(path.unlink, True)

    def _resolve(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if path != self.root and self.root not in path.parents:
            raise BusinessRuleError("Chave de armazenamento invalida.")
        return path

    @staticmethod
    def _write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_bytes(content)
        temporary.replace(path)


class AwsS3Storage:
    provider = "s3"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bucket = settings.storage_bucket
        if not self.bucket:
            raise ValueError("STORAGE_BUCKET e obrigatorio para usar AWS S3.")
        self.client = self._client(self.bucket)

    async def save(
        self, *, tenant_id: int, filename: str, extension: str, content: bytes
    ) -> StoredObject:
        key, stored_name = _object_key(tenant_id, extension)
        await anyio.to_thread.run_sync(
            lambda: self.client.upload_file(
                key,
                content,
                content_type=mimetypes.guess_type(filename)[0],
            )
        )
        return StoredObject(self.provider, self.bucket, key, stored_name)

    async def read(self, *, bucket: str | None, key: str) -> bytes:
        selected_bucket = bucket or self.bucket
        response = await anyio.to_thread.run_sync(
            lambda: self._client(selected_bucket).s3_client.get_object(
                Bucket=selected_bucket, Key=key
            )
        )
        return await anyio.to_thread.run_sync(response["Body"].read)

    async def delete(self, *, bucket: str | None, key: str) -> None:
        selected_bucket = bucket or self.bucket
        await anyio.to_thread.run_sync(
            self._client(selected_bucket).delete_file, key
        )

    def _client(self, bucket: str) -> AwsS3Client:
        endpoint = self.settings.storage_endpoint_url or None
        if endpoint and "://" not in endpoint:
            scheme = "https" if self.settings.storage_use_ssl else "http"
            endpoint = f"{scheme}://{endpoint}"
        return AwsS3Client(
            bucket_name=bucket,
            region_name=self.settings.storage_region,
            access_key_id=self.settings.storage_access_key or None,
            secret_access_key=self.settings.storage_secret_key or None,
            endpoint_url=endpoint,
        )


class SeaweedStorage:
    provider = "seaweedfs"

    def __init__(self, settings: Settings) -> None:
        if not settings.seaweed_filer_url:
            raise ValueError("SEAWEED_FILER_URL e obrigatorio para usar SeaweedFS.")
        if not settings.seaweed_project_name:
            raise ValueError("SEAWEED_PROJECT_NAME e obrigatorio para usar SeaweedFS.")
        self.filer_url = settings.seaweed_filer_url
        self.project_name = settings.seaweed_project_name.strip("/")
        self.username = settings.seaweed_username or None
        self.password = settings.seaweed_password or None
        self.timeout_seconds = settings.seaweed_timeout_seconds
        self.client = SeaweedFilerClient.from_settings(settings)

    async def save(
        self, *, tenant_id: int, filename: str, extension: str, content: bytes
    ) -> StoredObject:
        key, stored_name = _object_key(tenant_id, extension)
        await anyio.to_thread.run_sync(
            lambda: self.client.upload_file(
                key,
                content,
                content_type=mimetypes.guess_type(filename)[0],
            )
        )
        return StoredObject(self.provider, self.project_name, key, stored_name)

    async def read(self, *, bucket: str | None, key: str) -> bytes:
        client = self._client(bucket or self.project_name)
        response = await anyio.to_thread.run_sync(
            lambda: httpx.get(
                client.get_file_url(key),
                auth=client.auth,
                timeout=client.timeout_seconds,
            )
        )
        if response.status_code == 404:
            raise BusinessRuleError(
                "Conteudo do arquivo nao foi encontrado no storage.",
                code="storage_object_not_found",
            )
        response.raise_for_status()
        return response.content

    async def delete(self, *, bucket: str | None, key: str) -> None:
        client = self._client(bucket or self.project_name)
        deleted = await anyio.to_thread.run_sync(client.delete_file, key)
        if not deleted:
            raise RuntimeError("Falha ao remover arquivo do SeaweedFS.")

    def _client(self, project_name: str) -> SeaweedFilerClient:
        return SeaweedFilerClient(
            filer_url=self.filer_url,
            project_name=project_name,
            username=self.username,
            password=self.password,
            timeout_seconds=self.timeout_seconds,
        )

def get_storage(settings: Settings, provider: str | None = None) -> StorageAdapter:
    selected = provider or settings.storage_provider
    if selected == "local":
        return LocalStorage(settings.storage_local_path)
    if selected == "s3":
        return AwsS3Storage(settings)
    if selected == "seaweedfs":
        return SeaweedStorage(settings)
    raise ValueError(f"Provedor de storage nao suportado: {selected}.")


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    return re.sub(r"[^A-Za-z0-9._() -]", "_", name)[:255] or "arquivo"
