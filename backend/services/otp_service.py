from __future__ import annotations

import logging
import re
import random
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock

import httpx

from core.config import settings

logger = logging.getLogger("loanease.otp")

OTP_LENGTH = 6
OTP_TTL_MINUTES = int(getattr(settings, "OTP_EXPIRY_MINUTES", 5))
MAX_VERIFY_ATTEMPTS = 3
MAX_RESENDS = 3


@dataclass
class OtpRecord:
    mobile: str
    otp: str
    expires_at: datetime
    attempts: int = 0
    resend_count: int = 0
    verified: bool = False
    locked: bool = False
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OtpStore:
    def __init__(self) -> None:
        self._records: dict[str, OtpRecord] = {}
        self._lock = Lock()

    def _generate_otp(self) -> str:
        return "".join(random.choices(string.digits, k=OTP_LENGTH))

    def _create_record(self, session_id: str, mobile: str) -> OtpRecord:
        record = OtpRecord(
            mobile=mobile,
            otp=self._generate_otp(),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
        )
        self._records[session_id] = record
        return record

    def send_otp(self, session_id: str, mobile: str, *, force_new: bool = True) -> dict:
        with self._lock:
            record = self._records.get(session_id)
            if record is None or force_new:
                record = self._create_record(session_id, mobile)
            else:
                record.mobile = mobile
                record.updated_at = datetime.now(timezone.utc)
                record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)

        delivered = self._dispatch_otp(record.mobile, record.otp)
        return {
            "session_id": session_id,
            "mobile_last4": record.mobile[-4:],
            "expires_in_seconds": OTP_TTL_MINUTES * 60,
            "resend_count": record.resend_count,
            "sent": delivered,
            "demo_otp": record.otp if self._use_demo_provider() else None,
        }

    def resend_otp(self, session_id: str) -> dict:
        with self._lock:
            record = self._records.get(session_id)
            if record is None:
                raise KeyError("OTP session not initialized")
            if record.resend_count >= MAX_RESENDS:
                raise ValueError("Maximum OTP resend limit reached")
            record.otp = self._generate_otp()
            record.resend_count += 1
            record.attempts = 0
            record.locked = False
            record.verified = False
            record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)
            record.updated_at = datetime.now(timezone.utc)
            otp = record.otp
            mobile = record.mobile

        delivered = self._dispatch_otp(mobile, otp)
        return {
            "session_id": session_id,
            "mobile_last4": mobile[-4:],
            "expires_in_seconds": OTP_TTL_MINUTES * 60,
            "resend_count": self._records[session_id].resend_count,
            "sent": delivered,
            "demo_otp": otp if self._use_demo_provider() else None,
        }

    def verify_otp(self, session_id: str, otp_input: str) -> dict:
        with self._lock:
            record = self._records.get(session_id)
            if record is None:
                raise KeyError("OTP session not initialized")

            now = datetime.now(timezone.utc)
            if record.locked:
                return self._verification_response(record, verified=False, terminated=True, reason="OTP locked")
            if now > record.expires_at:
                record.locked = True
                return self._verification_response(record, verified=False, terminated=True, reason="OTP expired")

            normalized = re_digits(otp_input)
            if normalized == record.otp:
                record.verified = True
                record.locked = True
                return self._verification_response(record, verified=True, terminated=False)

            record.attempts += 1
            if record.attempts >= MAX_VERIFY_ATTEMPTS:
                record.locked = True
                return self._verification_response(record, verified=False, terminated=True, reason="Maximum attempts exceeded")

            return self._verification_response(record, verified=False, terminated=False, reason="OTP mismatch")

    def _verification_response(self, record: OtpRecord, *, verified: bool, terminated: bool, reason: str | None = None) -> dict:
        attempts_remaining = max(0, MAX_VERIFY_ATTEMPTS - record.attempts)
        return {
            "verified": verified,
            "terminated": terminated,
            "attempts_remaining": attempts_remaining,
            "mobile_last4": record.mobile[-4:],
            "expires_in_seconds": max(0, int((record.expires_at - datetime.now(timezone.utc)).total_seconds())),
            "reason": reason,
        }

    def _dispatch_otp(self, mobile: str, otp: str) -> bool:
        provider = (getattr(settings, "SMS_PROVIDER", "").strip().lower() or "auto")

        if provider in {"demo", "mock"}:
            logger.info("DEMO OTP for XXXXXX%s: %s", mobile[-4:], otp)
            return True

        if provider == "auto":
            for candidate in ("fast2sms", "textbelt", "twilio", "webhook"):
                delivered = self._dispatch_with_provider(candidate, mobile, otp)
                if delivered is not None:
                    return delivered
            logger.warning("No usable SMS provider configured")
            return False

        delivered = self._dispatch_with_provider(provider, mobile, otp)
        if delivered is not None:
            return delivered

        logger.warning("Unsupported SMS provider '%s'", provider)
        return False

    def _use_demo_provider(self) -> bool:
        provider = (getattr(settings, "SMS_PROVIDER", "").strip().lower() or "auto")
        return provider in {"demo", "mock"}

    def _dispatch_with_provider(self, provider: str, mobile: str, otp: str) -> bool | None:
        if provider == "fast2sms":
            api_key = getattr(settings, "FAST2SMS_API_KEY", "")
            if not api_key:
                return None
            return self._send_fast2sms(mobile, otp)
        if provider == "textbelt":
            api_key = getattr(settings, "TEXTBELT_API_KEY", "")
            if not api_key:
                return None
            return self._send_textbelt(mobile, otp)
        if provider == "twilio":
            account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
            auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
            from_number = getattr(settings, "TWILIO_FROM_NUMBER", "")
            if not account_sid or not auth_token or not from_number:
                return None
            return self._send_twilio(mobile, otp)
        if provider == "webhook":
            webhook_url = getattr(settings, "SMS_WEBHOOK_URL", "")
            if not webhook_url:
                return None
            return self._send_webhook(mobile, otp)

        return None

    def _send_fast2sms(self, mobile: str, otp: str) -> bool:
        api_key = getattr(settings, "FAST2SMS_API_KEY", "")
        if not api_key:
            logger.warning("FAST2SMS_API_KEY missing; cannot deliver OTP")
            return False

        payload = {
            "route": "otp",
            "variables_values": otp,
            "numbers": mobile,
        }
        headers = {"authorization": api_key, "accept": "application/json"}

        try:
            with httpx.Client(timeout=15) as client:
                response = client.post("https://www.fast2sms.com/dev/bulkV2", data=payload, headers=headers)
                response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Fast2SMS OTP dispatch failed: %s", str(exc))
            return False

    def _send_textbelt(self, mobile: str, otp: str) -> bool:
        api_key = getattr(settings, "TEXTBELT_API_KEY", "")
        if not api_key:
            logger.warning("TEXTBELT_API_KEY missing; cannot deliver OTP")
            return False

        payload = {
            "phone": mobile,
            "message": f"Your LoanEase OTP is {otp}. It expires in {OTP_TTL_MINUTES} minutes.",
            "key": api_key,
        }

        try:
            with httpx.Client(timeout=15) as client:
                response = client.post("https://textbelt.com/text", data=payload)
                response.raise_for_status()
                body = response.json()
            return bool(body.get("success"))
        except Exception as exc:
            logger.error("Textbelt OTP dispatch failed: %s", str(exc))
            return False

    def _send_webhook(self, mobile: str, otp: str) -> bool:
        webhook_url = getattr(settings, "SMS_WEBHOOK_URL", "")
        if not webhook_url:
            logger.warning("SMS_WEBHOOK_URL missing; cannot deliver OTP")
            return False

        payload = {
            "phone": mobile,
            "message": f"Your LoanEase OTP is {otp}. It expires in {OTP_TTL_MINUTES} minutes.",
            "otp": otp,
        }

        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(webhook_url, json=payload)
                response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Webhook OTP dispatch failed: %s", str(exc))
            return False

    def _send_twilio(self, mobile: str, otp: str) -> bool:
        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        from_number = getattr(settings, "TWILIO_FROM_NUMBER", "")
        if not account_sid or not auth_token or not from_number:
            logger.warning("Twilio credentials missing; cannot deliver OTP")
            return False

        message = f"Your LoanEase OTP is {otp}. It expires in {OTP_TTL_MINUTES} minutes."
        payload = {
            "To": f"+91{mobile}",
            "From": from_number,
            "Body": message,
        }

        try:
            with httpx.Client(timeout=15, auth=(account_sid, auth_token)) as client:
                response = client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                    data=payload,
                )
                response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Twilio OTP dispatch failed: %s", str(exc))
            return False


def re_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


otp_store = OtpStore()
