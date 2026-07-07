from __future__ import annotations

from typing import Any, BinaryIO
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]

from app.core.config import Settings


class AwsS3Client:
    def __init__(
        self,
        bucket_name: str,
        region_name: str,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        session_token: str | None = None,
        endpoint_url: str | None = None,
        public_url: str | None = None,
    ) -> None:
        if not bucket_name:
            raise ValueError("AWS_S3_BUCKET_NAME deve ser configurado para usar S3.")

        self.bucket_name = bucket_name
        self.region_name = region_name
        self.public_url = public_url.rstrip("/") if public_url else None
        self.s3_client = boto3.client(
            "s3",
            region_name=region_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
            endpoint_url=endpoint_url,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> AwsS3Client:
        return cls(
            bucket_name=settings.storage_bucket,
            region_name=settings.storage_region,
            access_key_id=settings.storage_access_key or None,
            secret_access_key=settings.storage_secret_key or None,
            endpoint_url=settings.storage_endpoint_url or None,
        )

    def upload_file(
        self,
        remote_filename: str,
        file_bytes_or_path: bytes | str | BinaryIO,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        object_key = self._normalize_key(remote_filename)
        extra_args = {"ContentType": content_type} if content_type else None

        try:
            if isinstance(file_bytes_or_path, str):
                self.s3_client.upload_file(
                    file_bytes_or_path,
                    self.bucket_name,
                    object_key,
                    ExtraArgs=extra_args or {},
                )
            else:
                self.s3_client.upload_fileobj(
                    self._as_fileobj(file_bytes_or_path),
                    self.bucket_name,
                    object_key,
                    ExtraArgs=extra_args or {},
                )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Falha no upload para AWS S3: {exc}") from exc

        return {
            "bucket": self.bucket_name,
            "key": object_key,
            "url": self.get_file_url(object_key),
        }

    def get_file_url(self, remote_filename: str) -> str:
        object_key = self._normalize_key(remote_filename)
        encoded_key = "/".join(quote(part) for part in object_key.split("/"))

        if self.public_url:
            return f"{self.public_url}/{encoded_key}"

        return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{encoded_key}"

    def delete_file(self, remote_filename: str) -> bool:
        object_key = self._normalize_key(remote_filename)

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Falha ao remover arquivo do AWS S3: {exc}") from exc

        return True

    def _normalize_key(self, remote_filename: str) -> str:
        return remote_filename.strip("/")

    def _as_fileobj(self, value: bytes | BinaryIO) -> BinaryIO:
        if isinstance(value, bytes):
            from io import BytesIO

            return BytesIO(value)

        return value
