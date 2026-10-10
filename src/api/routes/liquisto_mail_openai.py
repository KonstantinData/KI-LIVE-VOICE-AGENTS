"""Disabled-by-default synthetic OpenAI pilot with a distinct signed purpose."""
from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import stat
import time
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.api.config import get_settings
from src.api.routes.assistant import AssistantContextItem
from src.api.routes.liquisto_mail import (
    Closed, MailReceipt, MailRespondRequest, _json, _key, build_mail_messages,
    canonical_receipt, get_mail_settings,
)
from src.api.services.liquisto_mail import _protected_path, _protected_stat
from src.api.services.liquisto_mail_openai import (
    BUDGET_MICRO_USD, MAX_ATTEMPTS, RESERVATION_MICRO_USD,
    MailOpenAIError, generate_answer, request_bytes,
)
from src.api.services.liquisto_openai_budget import OpenAIHttpBudget

router = APIRouter(prefix="/assistant/mail/openai", tags=["Liquisto Mail OpenAI Pilot"])
SOURCE = "synthetic-public-reference"
MAX_REQUEST_BYTES = 12_000


class OpenAIMailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OLIVIA_MAIL_OPENAI_", extra="ignore")
    enabled: bool = False
    api_key: SecretStr = Field(default=SecretStr(""), validation_alias="OLIVIA_OPENAI_API_KEY")
    ledger_path: str = ""
    pilot_sha256: str = ""
    max_requests: int = Field(default=0, ge=0, le=5)


@lru_cache
def get_openai_mail_settings() -> OpenAIMailSettings:
    return OpenAIMailSettings()


class OpenAIMailRequest(MailRespondRequest):
    contract_version: Literal["olivia-mail-openai-respond-v1"]
    data_policy: Literal["synthetic-only-v1"]
    pilot_id: Annotated[str, Field(pattern=r"^olivia-openai-pilot-[a-z0-9-]{1,80}$")]
    prompt: str = Field(min_length=2, max_length=1200)
    context: list[AssistantContextItem] = Field(max_length=1)

    @model_validator(mode="after")
    def bounded_sources(self):
        # Override the local-only source validator. Existing CRM grants are invalid here.
        from src.api.services.liquisto_mail import APPROVED_RECIPIENTS

        if self.recipient not in APPROVED_RECIPIENTS:
            raise ValueError("unapproved correspondent")
        if self.source_ids not in ([], [SOURCE]):
            raise ValueError("only an explicitly synthetic source is permitted")
        if [item.source_id for item in self.context] != self.source_ids:
            raise ValueError("context must match the signed source set")
        for item in self.context:
            if (item.system, item.permission, item.classification) != (
                "liquisto-synthetic-test-fixture", "synthetic:read", "public",
            ):
                raise ValueError("synthetic fixture metadata required")
        return self


class OpenAIReceipt(MailReceipt):
    contract_version: Literal["olivia-openai-receipt-v1"]
    operation: Literal["respond-openai"]
    provider: Literal["openai"]
    model: Literal["gpt-6-luna"]
    data_policy: Literal["synthetic-only-v1"]
    pilot_id: Annotated[str, Field(pattern=r"^olivia-openai-pilot-[a-z0-9-]{1,80}$")]
    pilot_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    max_input_tokens: Literal[8192]
    max_output_tokens: Literal[512]
    max_attempts: Literal[5]
    budget_micro_usd: Literal[100000]
    price_snapshot: Literal["openai-gpt-6-luna-standard-20261010"]


class SignedOpenAIReceipt(Closed):
    receipt: OpenAIReceipt
    signature: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def reserve_attempt(settings: OpenAIMailSettings, signed: SignedOpenAIReceipt,
                    raw: bytes, payload: OpenAIMailRequest) -> None:
    """Authenticate a new egress purpose, then atomically consume replay and quota."""
    receipt = signed.receipt
    fields = ("tenant_id", "agent_id", "principal_id", "recipient", "profile_id",
              "profile_sha256", "message_key", "source_ids", "data_policy", "pilot_id")
    try:
        expected = hmac.new(
            _key(get_mail_settings().receipt_key_path),
            canonical_receipt(receipt.model_dump()), hashlib.sha256,
        ).hexdigest()
        if (not hmac.compare_digest(expected, signed.signature)
                or receipt.payload_sha256 != hashlib.sha256(raw).hexdigest()
                or any(getattr(receipt, name) != getattr(payload, name) for name in fields)
                or receipt.pilot_sha256 != settings.pilot_sha256
                or not 0 < receipt.expires_at - int(time.time()) <= 60):
            raise ValueError("receipt denied")
    except Exception:
        raise HTTPException(403, "mail_openai_receipt_denied") from None
    try:
        path = Path(settings.ledger_path)
        _protected_path(path)
        _protected_path(path.parent)
        if not path.exists():
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
            except FileExistsError:
                pass
        info = path.stat()
        _protected_stat(info)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("ledger must be a regular file")
        with closing(sqlite3.connect(path, timeout=15)) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("CREATE TABLE IF NOT EXISTS openai_mail_attempts "
                           "(nonce_hash TEXT PRIMARY KEY, message_hash TEXT UNIQUE NOT NULL)")
                nonce = hashlib.sha256(receipt.nonce.encode()).hexdigest()
                binding = hashlib.sha256(canonical_receipt({
                    "principal_id": receipt.principal_id, "message_key": receipt.message_key,
                    "profile_sha256": receipt.profile_sha256,
                })).hexdigest()
                if db.execute("SELECT 1 FROM openai_mail_attempts WHERE nonce_hash=? "
                              "OR message_hash=?", (nonce, binding)).fetchone():
                    raise HTTPException(409, "mail_openai_receipt_replayed")
                count = db.execute("SELECT COUNT(*) FROM openai_mail_attempts").fetchone()[0]
                if (count >= min(settings.max_requests, MAX_ATTEMPTS)
                        or (count + 1) * RESERVATION_MICRO_USD > BUDGET_MICRO_USD):
                    raise HTTPException(429, "mail_openai_pilot_limit_reached")
                db.execute("INSERT INTO openai_mail_attempts VALUES (?, ?)", (nonce, binding))
                db.commit()
            except Exception:
                db.rollback()
                raise
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "mail_openai_ledger_unavailable") from None


@router.post("/respond")
async def respond(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_olivia_mail_receipt: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    try:
        settings = get_openai_mail_settings()
        mail = get_mail_settings()
    except ValidationError:
        raise HTTPException(503, "mail_openai_configuration_unavailable") from None
    if not settings.enabled or not mail.enabled:
        raise HTTPException(503, "mail_openai_disabled")
    if (not settings.api_key.get_secret_value().strip() or settings.max_requests < 1
            or not settings.ledger_path or len(mail.runtime_token) < 32
            or len(settings.pilot_sha256) != 64
            or not mail.runtime_token.isascii()
            or any(char.isspace() for char in mail.runtime_token)
            or mail.runtime_token == get_settings().liquisto_assistant_service_token):
        raise HTTPException(503, "mail_openai_configuration_unavailable")
    if not authorization or not authorization.isascii() or not hmac.compare_digest(
        authorization, "Bearer " + mail.runtime_token,
    ):
        raise HTTPException(401, "mail_authentication_required")
    content_type = [part.strip().lower() for part in request.headers.get("content-type", "").split(";")]
    if content_type[0] != "application/json" or any(
        part not in {"charset=utf-8", 'charset="utf-8"'} for part in content_type[1:]
    ):
        raise HTTPException(415, "mail_json_required")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_REQUEST_BYTES:
            raise HTTPException(413, "mail_request_too_large")
    try:
        if not x_olivia_mail_receipt or len(x_olivia_mail_receipt) > 8000:
            raise ValueError("missing receipt")
        payload = OpenAIMailRequest.model_validate(_json(bytes(raw)))
        signed = SignedOpenAIReceipt.model_validate(_json(x_olivia_mail_receipt))
        messages = build_mail_messages(
            prompt=payload.prompt,
            context=[item.model_dump(mode="json") for item in payload.context],
        )
        encoded = request_bytes(messages)
    except (ValueError, ValidationError, TypeError, MailOpenAIError):
        raise HTTPException(422, "mail_openai_contract_invalid") from None
    reserve_attempt(settings, signed, bytes(raw), payload)
    try:
        answer = await generate_answer(settings.api_key, encoded, budget=OpenAIHttpBudget(Path(settings.ledger_path)))
        return {"contract_version": "olivia-mail-answer-v1", "answer": answer}
    except MailOpenAIError:
        raise HTTPException(502, "mail_openai_generation_unavailable") from None
