from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote

import httpx

from app.core.config import Settings


class SeaweedFilerClient:
    def __init__(
        self,
        filer_url: str,
        project_name: str,
        username: str | None = None,
        password: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.filer_url = filer_url.rstrip("/")
        self.project_name = project_name.strip("/")
        self.timeout_seconds = timeout_seconds
        self.auth = (username, password) if username and password else None

    @classmethod
    def from_settings(cls, settings: Settings) -> SeaweedFilerClient:
        return cls(
            filer_url=settings.seaweed_filer_url,
            project_name=settings.seaweed_project_name,
            username=settings.seaweed_username or None,
            password=settings.seaweed_password or None,
            timeout_seconds=settings.seaweed_timeout_seconds,
        )

    def upload_file(
        self,
        remote_filename: str,
        file_bytes_or_path: bytes | str | BinaryIO,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        url = self._build_url(remote_filename)
        files = self._build_multipart_file(remote_filename, file_bytes_or_path, content_type)

        close_file = getattr(files["file"][1], "close", None)
        try:
            response = httpx.post(
                url,
                files=files,
                auth=self.auth,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return self._response_payload(response)
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Falha no upload para SeaweedFS: {exc.response.status_code} - {exc.response.text}"
            ) from exc
        finally:
            if isinstance(file_bytes_or_path, str) and callable(close_file):
                close_file()

    def get_file_url(self, remote_filename: str) -> str:
        return self._build_url(remote_filename)

    def delete_file(self, remote_filename: str) -> bool:
        response = httpx.delete(
            self._build_url(remote_filename),
            auth=self.auth,
            timeout=self.timeout_seconds,
        )
        return response.status_code in {200, 202, 204, 404}

    def _build_url(self, remote_filename: str) -> str:
        path_parts = [self.project_name, *remote_filename.strip("/").split("/")]
        encoded_path = "/".join(quote(part) for part in path_parts if part)
        return f"{self.filer_url}/{encoded_path}"

    def _build_multipart_file(
        self,
        remote_filename: str,
        file_bytes_or_path: bytes | str | BinaryIO,
        content_type: str | None,
    ) -> dict[str, Any]:
        filename = Path(remote_filename).name

        if isinstance(file_bytes_or_path, str):
            # O handle é fechado pelo bloco finally de upload_file.
            file_handle = open(file_bytes_or_path, "rb")  # noqa: SIM115
            filename = Path(file_bytes_or_path).name
            return {"file": (filename, file_handle, content_type)}

        return {"file": (filename, file_bytes_or_path, content_type)}

    def _response_payload(self, response: httpx.Response) -> dict[str, Any]:
        if not response.content:
            return {"url": str(response.url)}

        try:
            payload = response.json()
        except ValueError:
            return {"url": str(response.url), "text": response.text}

        return payload if isinstance(payload, dict) else {"data": payload}
