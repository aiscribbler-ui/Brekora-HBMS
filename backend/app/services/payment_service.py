import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.booking import Booking, BookingStatus
from app.models.failed_payment import FailedPayment
from app.models.inventory_hold import InventoryHold
from app.models.payment import Payment
from app.models.user import User
from app.repositories.booking import BookingRepository
from app.repositories.payment import PaymentRepository
from app.services.inventory_service import InventoryService
from app.services.razorpay_client import RazorpayClient

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for Razorpay order creation and webhook processing."""

    def __init__(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        redis: Redis | None = None,
    ):
        self.session = session
        self.org_id = org_id
        self.redis = redis
        self.razorpay = RazorpayClient()
        self.payment_repo = PaymentRepository(session, org_id)
        self.booking_repo = BookingRepository(session, org_id)

    async def create_order(self, booking_id: uuid.UUID) -> dict:
        """Create a Razorpay order for a pending booking.

        Returns the Razorpay order dict.
        """
        booking = await self.booking_repo.get(booking_id)
        if not booking:
            raise ValueError("Booking not found")
        if booking.status != BookingStatus.pending_payment.value:
            raise ValueError(
                f"Booking status must be pending_payment, got {booking.status}"
            )

        amount = booking.total_amount
        currency = booking.currency or "INR"
        receipt = f"booking_{booking.id}"

        order = self.razorpay.create_order(
            amount=amount,
            currency=currency,
            receipt=receipt,
            notes={"org_id": str(self.org_id), "booking_id": str(booking_id)},
        )

        payment = Payment(
            org_id=self.org_id,
            booking_id=booking_id,
            amount=amount,
            currency=currency,
            provider="razorpay",
            provider_order_id=order["id"],
            status="created",
        )
        self.session.add(payment)
        await self.session.flush()
        await self.session.refresh(payment)

        return order

    async def create_difference_order(self, booking_id: uuid.UUID, amount: Decimal) -> dict:
        """Create a Razorpay order for a booking modification (additional charge).

        Returns the Razorpay order dict.
        """
        booking = await self.booking_repo.get(booking_id)
        if not booking:
            raise ValueError("Booking not found")

        currency = booking.currency or "INR"
        receipt = f"modification_{booking.id}"

        order = self.razorpay.create_order(
            amount=amount,
            currency=currency,
            receipt=receipt,
            notes={"org_id": str(self.org_id), "booking_id": str(booking_id), "type": "modification_difference"},
        )

        payment = Payment(
            org_id=self.org_id,
            booking_id=booking_id,
            amount=amount,
            currency=currency,
            provider="razorpay",
            provider_order_id=order["id"],
            status="created",
        )
        self.session.add(payment)
        await self.session.flush()
        await self.session.refresh(payment)

        return order

    async def process_webhook(self, payload: dict, signature: str) -> bool:
        """Process a Razorpay webhook event.

        Verifies signature, idempotency via Redis, and handles:
        - payment.captured -> commit inventory, confirm booking
        - payment.failed -> release inventory, mark payment_failed

        Returns True if processed (or already processed), False on unhandled event.
        """
        settings = get_settings()
        secret = settings.RAZORPAY_WEBHOOK_SECRET or ""

        import json
        body = json.dumps(payload, separators=(",", ":")).encode()
        if not self.razorpay.verify_webhook_signature(body, signature, secret):
            logger.warning("Razorpay webhook signature verification failed")
            return False

        event = payload.get("event")
        event_id = payload.get("id", "")
        if not event_id:
            event_id = f"razorpay_{event}_{payload.get('created_at', '')}"

        # Idempotency: check Redis for processed event
        if self.redis:
            processed = await self.redis.get(f"webhook:{event_id}")
            if processed:
                logger.info("Webhook event %s already processed", event_id)
                return True

        if event == "payment.captured":
            await self._handle_payment_captured(payload)
        elif event == "payment.failed":
            await self._handle_payment_failed(payload)
        else:
            logger.info("Unhandled Razorpay webhook event: %s", event)
            return False

        if self.redis:
            await self.redis.setex(f"webhook:{event_id}", 86400, "1")
        return True

    async def _handle_payment_captured(self, payload: dict) -> None:
        """Commit inventory and confirm booking on successful payment."""
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        if not order_id:
            logger.error("payment.captured webhook missing order_id")
            return

        # Find payment record by order id
        stmt = select(Payment).where(Payment.provider_order_id == order_id)
        result = await self.session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            logger.error("Payment record not found for order %s", order_id)
            return

        booking = await self.booking_repo.get(payment.booking_id)
        if not booking:
            logger.error("Booking not found for payment %s", payment.id)
            return

        # Commit inventory via hold linked to booking
        hold_stmt = select(InventoryHold).where(
            InventoryHold.booking_id == booking.id,
            InventoryHold.status == "active",
        )
        hold_result = await self.session.execute(hold_stmt)
        hold = hold_result.scalar_one_or_none()

        if hold:
            inventory_svc = InventoryService(self.session, self.redis)
            try:
                await inventory_svc.commit_inventory(hold.id)
            except Exception as exc:
                logger.error("Inventory commit failed for hold %s: %s", hold.id, exc)
                # Still proceed to confirm booking; inventory may already be committed

        # Update booking status
        booking.status = BookingStatus.confirmed.value
        await self.session.flush()

        # Update payment status
        payment.status = "captured"
        payment.provider_payment_id = payment_id
        await self.session.flush()

        logger.info(
            "Booking %s confirmed, payment %s captured", booking.id, payment.id
        )

        # Confirmation notification stub (MVP: log only)
        guest_email = "unknown"
        if booking.guest_id:
            user_result = await self.session.execute(
                select(User.email).where(User.id == booking.guest_id)
            )
            email = user_result.scalar_one_or_none()
            if email:
                guest_email = email
        logger.info(
            "Payment confirmation notification stub for booking %s, guest email %s",
            booking.id,
            guest_email,
        )

    async def _handle_payment_failed(self, payload: dict) -> None:
        """Release inventory and mark booking as payment_failed."""
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        error_reason = payment_entity.get("error_description", "unknown")

        if not order_id:
            # Fallback: try to get from payload
            order_id = payload.get("payload", {}).get("order", {}).get("entity", {}).get("id")

        if not order_id:
            logger.error("payment.failed webhook missing order_id")
            return

        stmt = select(Payment).where(Payment.provider_order_id == order_id)
        result = await self.session.execute(stmt)
        payment = result.scalar_one_or_none()
        if not payment:
            logger.error("Payment record not found for order %s", order_id)
            return

        booking = await self.booking_repo.get(payment.booking_id)
        if not booking:
            logger.error("Booking not found for payment %s", payment.id)
            return

        # Release inventory
        hold_stmt = select(InventoryHold).where(
            InventoryHold.booking_id == booking.id,
            InventoryHold.status == "active",
        )
        hold_result = await self.session.execute(hold_stmt)
        hold = hold_result.scalar_one_or_none()

        if hold:
            inventory_svc = InventoryService(self.session, self.redis)
            try:
                await inventory_svc.release_inventory(hold.id)
            except Exception as exc:
                logger.error("Inventory release failed for hold %s: %s", hold.id, exc)

        # Update statuses
        booking.status = BookingStatus.payment_failed.value
        await self.session.flush()

        payment.status = "failed"
        await self.session.flush()

        # Record failure attempt
        max_stmt = select(func.max(FailedPayment.attempt_number)).where(
            FailedPayment.booking_id == booking.id,
            FailedPayment.org_id == self.org_id,
        )
        max_result = await self.session.execute(max_stmt)
        max_attempt = max_result.scalar_one_or_none() or 0
        failed_payment = FailedPayment(
            org_id=self.org_id,
            booking_id=booking.id,
            reason=error_reason,
            attempt_number=max_attempt + 1,
        )
        self.session.add(failed_payment)
        await self.session.flush()

        logger.info(
            "Booking %s marked payment_failed (reason: %s), payment %s failed",
            booking.id,
            error_reason,
            payment.id,
        )

    async def check_payment_timeouts(self) -> int:
        """Find pending bookings older than 10 minutes without captured payment.

        Release inventory, mark booking as payment_failed, and create a
        FailedPayment record with reason="timeout".

        Returns the number of bookings timed out.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
        stmt = select(Booking).where(
            Booking.status == BookingStatus.pending_payment.value,
            Booking.created_at < cutoff,
            Booking.org_id == self.org_id,
        )
        result = await self.session.execute(stmt)
        bookings = result.scalars().all()
        timed_out = 0

        for booking in bookings:
            # Skip if a captured payment already exists
            pay_stmt = select(Payment).where(
                Payment.booking_id == booking.id,
                Payment.status == "captured",
            )
            pay_result = await self.session.execute(pay_stmt)
            if pay_result.scalar_one_or_none():
                continue

            # Release inventory
            hold_stmt = select(InventoryHold).where(
                InventoryHold.booking_id == booking.id,
                InventoryHold.status == "active",
            )
            hold_result = await self.session.execute(hold_stmt)
            hold = hold_result.scalar_one_or_none()
            if hold:
                inventory_svc = InventoryService(self.session, self.redis)
                try:
                    await inventory_svc.release_inventory(hold.id)
                except Exception as exc:
                    logger.error("Inventory release failed for hold %s: %s", hold.id, exc)

            booking.status = BookingStatus.payment_failed.value

            max_stmt = select(func.max(FailedPayment.attempt_number)).where(
                FailedPayment.booking_id == booking.id,
                FailedPayment.org_id == self.org_id,
            )
            max_result = await self.session.execute(max_stmt)
            max_attempt = max_result.scalar_one_or_none() or 0
            failed_payment = FailedPayment(
                org_id=self.org_id,
                booking_id=booking.id,
                reason="timeout",
                attempt_number=max_attempt + 1,
            )
            self.session.add(failed_payment)
            timed_out += 1

        if timed_out:
            await self.session.flush()
        return timed_out
