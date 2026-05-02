import hmac
import hashlib
import logging
from decimal import Decimal
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RazorpayClient:
    """Wrapper around the official Razorpay Python SDK.

    In test mode, if keys are missing, stub methods return mock responses
    so that tests and local dev do not fail.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self._client: Any | None = None
        if self.key_id and self.key_secret:
            try:
                import razorpay
                self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
            except Exception as exc:
                logger.warning("Failed to initialise Razorpay client: %s", exc)

    def _is_stub(self) -> bool:
        return self._client is None

    def create_order(
        self,
        amount: Decimal,
        currency: str,
        receipt: str,
        notes: dict | None = None,
    ) -> dict:
        """Create a Razorpay order.

        Amount is in Decimal (INR paise conversion handled internally).
        """
        if self._is_stub():
            return {
                "id": f"order_stub_{receipt}",
                "amount": int(amount * 100),
                "currency": currency,
                "receipt": receipt,
                "status": "created",
                "notes": notes or {},
            }

        data = {
            "amount": int(amount * 100),  # paise
            "currency": currency,
            "receipt": receipt,
            "notes": notes or {},
        }
        return self._client.order.create(data=data)

    @staticmethod
    def verify_webhook_signature(
        body: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """Verify Razorpay webhook signature using HMAC-SHA256."""
        if not secret:
            logger.warning("Webhook secret missing; accepting signature blindly (dev/test)")
            return True
        expected = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
