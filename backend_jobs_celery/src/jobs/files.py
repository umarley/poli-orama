"""Extracao de texto de PDF e OCR de imagens."""

from io import BytesIO
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from jobs.config import Settings
from jobs.database import normalize_database_url
from jobs.file_storage import read_object


class FileExtractionProcessor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database_url = normalize_database_url(settings.jobs_database_url)

    def extract(self, *, tenant_id: int, attachment_id: int) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            connection.execute(
                "SELECT set_config('app.current_tenant_id', %s, true)",
                (str(tenant_id),),
            )
            item = connection.execute(
                """
                SELECT ar.id AS arquivo_id, ar.extensao, ar.provedor_storage,
                       ar.bucket, ar.caminho
                FROM arquivo.anexo an
                JOIN arquivo.arquivo ar ON ar.id=an.arquivo_id
                WHERE an.tenant_id=%s AND an.id=%s
                  AND an.excluido_em IS NULL AND ar.excluido_em IS NULL
                """,
                (tenant_id, attachment_id),
            ).fetchone()
            if item is None:
                raise LookupError("Anexo nao encontrado.")
            content = read_object(
                self.settings,
                provider=str(item["provedor_storage"]),
                bucket=item["bucket"],
                key=str(item["caminho"]),
            )
            extension = str(item["extensao"] or "").lower()
            if extension == "pdf":
                text_value, metadata, method = self._extract_pdf(content)
            elif extension in {"jpg", "jpeg", "png", "webp"}:
                text_value, metadata, method = self._extract_image(content)
            else:
                return {"arquivo_id": int(item["arquivo_id"]), "ignorado": True}
            connection.execute(
                "DELETE FROM arquivo.documento_extraido WHERE tenant_id=%s AND arquivo_id=%s",
                (tenant_id, item["arquivo_id"]),
            )
            connection.execute(
                """
                INSERT INTO arquivo.documento_extraido
                    (tenant_id,arquivo_id,texto_extraido,metadados,
                     metodo_extracao,idioma)
                VALUES (%s,%s,%s,%s,%s,'por')
                """,
                (
                    tenant_id,
                    item["arquivo_id"],
                    text_value,
                    Jsonb(metadata),
                    method,
                ),
            )
            return {
                "arquivo_id": int(item["arquivo_id"]),
                "metodo": method,
                "caracteres": len(text_value),
            }

    @staticmethod
    def _extract_pdf(content: bytes) -> tuple[str, dict[str, Any], str]:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        text_value = "\n\n".join(page for page in pages if page)
        return text_value, {"paginas": len(reader.pages)}, "pypdf"

    @staticmethod
    def _extract_image(content: bytes) -> tuple[str, dict[str, Any], str]:
        import pytesseract
        from PIL import Image

        with Image.open(BytesIO(content)) as image:
            text_value = pytesseract.image_to_string(image, lang="por").strip()
            metadata = {
                "largura": image.width,
                "altura": image.height,
                "formato": image.format,
            }
        return text_value, metadata, "tesseract_ocr"
