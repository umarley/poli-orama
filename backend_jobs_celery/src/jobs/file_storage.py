"""Leitura de objetos usados pelos jobs, sem expor o storage ao banco de dominio."""

from pathlib import Path
from typing import Any

from jobs.config import Settings


def read_object(settings: Settings, *, provider: str, bucket: str | None, key: str) -> bytes:
    if provider == "local":
        root = Path(settings.storage_local_path).resolve()
        path = (root / key).resolve()
        if root not in path.parents:
            raise ValueError("Chave de storage local invalida.")
        return path.read_bytes()
    if provider not in {"s3", "seaweedfs"}:
        raise ValueError(f"Storage nao suportado pelo worker: {provider}.")
    import boto3

    client: Any = boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url or None,
        region_name=settings.storage_region,
        aws_access_key_id=settings.storage_access_key or None,
        aws_secret_access_key=settings.storage_secret_key or None,
        use_ssl=settings.storage_use_ssl,
    )
    response = client.get_object(Bucket=bucket or settings.storage_bucket, Key=key)
    return bytes(response["Body"].read())
