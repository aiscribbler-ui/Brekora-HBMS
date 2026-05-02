from decimal import Decimal

from app.models.cancellation_policy import CancellationPolicy


class RefundCalculator:
    """Calculate refund amount based on cancellation policy and hours before check-in.

    Business rules:
    - GST and OTA commissions are NOT refundable to the guest.
      The caller should pass the net refundable amount (after deducting
      non-refundable components) as ``booking_amount``.
    - ``is_non_refundable`` always returns 0 regardless of window.
    - Free cancellation window = 100% refund.
    - Partial refund window = ``booking_amount * partial_refund_percentage / 100``.
    - Anything outside the above windows = 0 refund.
    """

    @staticmethod
    def calculate_refund(
        booking_amount: Decimal,
        policy: CancellationPolicy,
        hours_before_checkin: int,
    ) -> Decimal:
        if policy.is_non_refundable:
            return Decimal("0")

        if (
            policy.free_cancellation_hours is not None
            and hours_before_checkin >= policy.free_cancellation_hours
        ):
            return booking_amount

        if (
            policy.partial_refund_hours is not None
            and hours_before_checkin >= policy.partial_refund_hours
            and policy.partial_refund_percentage is not None
        ):
            return (
                booking_amount
                * policy.partial_refund_percentage
                / Decimal("100")
            ).quantize(Decimal("0.01"))

        return Decimal("0")
