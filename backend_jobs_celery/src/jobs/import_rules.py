"""Normalizacao e validacao deterministica para importacoes de pessoas."""

import re
import unicodedata
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FIELD_ALIASES = {
    "nome": "nome_completo",
    "nome_completo": "nome_completo",
    "nomecompleto": "nome_completo",
    "cpf": "cpf",
    "rg": "rg",
    "titulo": "titulo_eleitor",
    "titulo_eleitor": "titulo_eleitor",
    "tituloeleitor": "titulo_eleitor",
    "data_nascimento": "data_nascimento",
    "nascimento": "data_nascimento",
    "telefone": "telefone",
    "celular": "telefone",
    "whatsapp": "telefone",
    "email": "email",
    "e_mail": "email",
    "endereco": "endereco",
    "logradouro": "logradouro",
    "numero": "numero",
    "complemento": "complemento",
    "bairro": "bairro",
    "cidade": "municipio",
    "municipio": "municipio",
    "uf": "uf",
    "estado": "uf",
    "cep": "cep",
}


def normalize_header(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", ascii_value.lower())).strip("_")


def automatic_mapping(headers: list[str]) -> dict[str, str]:
    return {
        header: FIELD_ALIASES[key]
        for header in headers
        if (key := normalize_header(header)) in FIELD_ALIASES
    }


def normalize_cpf(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    if not digits:
        return None
    if len(digits) != 11 or digits == digits[0] * 11:
        raise ValueError("CPF deve possuir 11 digitos validos.")
    for size in (9, 10):
        total = sum(int(digits[index]) * (size + 1 - index) for index in range(size))
        check = (total * 10 % 11) % 10
        if check != int(digits[size]):
            raise ValueError("CPF invalido.")
    return digits


def normalize_phone(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    if not digits:
        return None
    if len(digits) in {10, 11}:
        digits = f"55{digits}"
    if len(digits) not in {12, 13} or not digits.startswith("55"):
        raise ValueError("Telefone deve conter DDD e numero validos.")
    return f"+{digits}"


def normalize_email(value: Any) -> str | None:
    email = str(value or "").strip().lower()
    if not email:
        return None
    if len(email) > 180 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("E-mail invalido.")
    return email


def normalize_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError("Data deve usar AAAA-MM-DD ou DD/MM/AAAA.")


def normalize_cep(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    if not digits:
        return None
    if len(digits) != 8:
        raise ValueError("CEP deve possuir 8 digitos.")
    return f"{digits[:5]}-{digits[5:]}"


def split_address(data: dict[str, Any]) -> dict[str, str | None]:
    address = str(data.get("endereco") or "").strip()
    parts = [part.strip() for part in address.split(",") if part.strip()]
    logradouro = str(data.get("logradouro") or (parts[0] if parts else "")).strip()
    number = str(data.get("numero") or (parts[1] if len(parts) > 1 else "")).strip()
    return {
        "endereco": address or None,
        "logradouro": logradouro or None,
        "numero": number or None,
        "complemento": str(data.get("complemento") or "").strip() or None,
        "bairro": str(data.get("bairro") or "").strip() or None,
        "municipio": str(data.get("municipio") or "").strip() or None,
        "uf": str(data.get("uf") or "").strip().upper()[:2] or None,
        "cep": normalize_cep(data.get("cep")),
    }


def name_similarity(left: str, right: str) -> float:
    return round(
        SequenceMatcher(
            None,
            normalize_header(left).replace("_", " "),
            normalize_header(right).replace("_", " "),
        ).ratio()
        * 100,
        2,
    )
