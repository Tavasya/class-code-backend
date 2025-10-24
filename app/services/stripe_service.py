# app/services/stripe_service.py
import stripe
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.stripe_config import (
    get_price_id,
    calculate_credits,
    STRIPE_WEBHOOK_SECRET
)
from app.models.stripe_model import (
    CheckoutRequest,
    CheckoutResponse,
    UpdateQuantityRequest,
    UpdateQuantityResponse,
    CancelSubscriptionRequest,
    CancelSubscriptionResponse,
    CustomerPortalRequest,
    CustomerPortalResponse
)

logger = logging.getLogger(__name__)

class StripeService:
    """Service for handling Stripe operations"""

    @staticmethod
    async def create_checkout_session(
        request: CheckoutRequest,
        base_url: str
    ) -> CheckoutResponse:
        """Create a Stripe checkout session for subscription purchase

        Args:
            request: Checkout request with plan details
            base_url: Base URL for success/cancel redirects

        Returns:
            CheckoutResponse with checkout URL

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        try:
            # Get the correct price ID
            price_id = get_price_id(request.plan_type, request.billing_cycle)

            # Set default URLs if not provided
            success_url = request.success_url or f"{base_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = request.cancel_url or f"{base_url}/subscription/cancel"

            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                mode='subscription',
                line_items=[{
                    'price': price_id,
                    'quantity': request.student_count,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'teacher_id': request.teacher_id,
                    'plan_type': request.plan_type,
                    'billing_cycle': request.billing_cycle,
                    'student_count': str(request.student_count)
                },
                subscription_data={
                    'metadata': {
                        'teacher_id': request.teacher_id,
                        'plan_type': request.plan_type,
                        'billing_cycle': request.billing_cycle,
                        'student_count': str(request.student_count)
                    }
                }
            )

            logger.info(
                f"Created checkout session for teacher {request.teacher_id}: "
                f"{request.plan_type} {request.billing_cycle} × {request.student_count} students"
            )

            return CheckoutResponse(
                checkout_url=session.url,
                session_id=session.id
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise

    @staticmethod
    async def update_subscription_quantity(
        request: UpdateQuantityRequest,
        stripe_subscription_id: str,
        plan_type: str
    ) -> UpdateQuantityResponse:
        """Update the student count (quantity) for an existing subscription

        Args:
            request: Update request with new student count
            stripe_subscription_id: Stripe subscription ID
            plan_type: Current plan type for credit calculation

        Returns:
            UpdateQuantityResponse with new credits

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        try:
            # Retrieve the subscription
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)

            # Update the subscription item quantity
            stripe.SubscriptionItem.modify(
                subscription['items']['data'][0].id,
                quantity=request.new_student_count
            )

            # Calculate new credits
            new_credits = calculate_credits(plan_type, request.new_student_count)

            logger.info(
                f"Updated subscription {stripe_subscription_id} quantity to {request.new_student_count} students. "
                f"New credits: {new_credits} hours"
            )

            return UpdateQuantityResponse(
                success=True,
                message=f"Successfully updated student count to {request.new_student_count}",
                new_credits=new_credits
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error updating subscription quantity: {str(e)}")
            return UpdateQuantityResponse(
                success=False,
                message=f"Failed to update subscription: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error updating subscription quantity: {str(e)}")
            return UpdateQuantityResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    @staticmethod
    async def cancel_subscription(
        request: CancelSubscriptionRequest,
        stripe_subscription_id: str
    ) -> CancelSubscriptionResponse:
        """Cancel a Stripe subscription

        Args:
            request: Cancellation request
            stripe_subscription_id: Stripe subscription ID

        Returns:
            CancelSubscriptionResponse

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        try:
            if request.cancel_at_period_end:
                # Cancel at end of billing period
                subscription = stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True
                )
                message = "Subscription will be canceled at the end of the current billing period"
                canceled_at = None
            else:
                # Cancel immediately
                subscription = stripe.Subscription.cancel(stripe_subscription_id)
                message = "Subscription canceled immediately"
                canceled_at = datetime.now()

            logger.info(f"Canceled subscription {stripe_subscription_id} for teacher {request.teacher_id}")

            return CancelSubscriptionResponse(
                success=True,
                message=message,
                canceled_at=canceled_at
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {str(e)}")
            return CancelSubscriptionResponse(
                success=False,
                message=f"Failed to cancel subscription: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return CancelSubscriptionResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    @staticmethod
    async def create_customer_portal_session(
        request: CustomerPortalRequest,
        stripe_customer_id: str,
        base_url: str
    ) -> CustomerPortalResponse:
        """Create a Stripe customer portal session

        Args:
            request: Portal request
            stripe_customer_id: Stripe customer ID
            base_url: Base URL for return after portal session

        Returns:
            CustomerPortalResponse with portal URL

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        try:
            return_url = request.return_url or f"{base_url}/subscription/manage"

            session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=return_url
            )

            logger.info(f"Created customer portal session for teacher {request.teacher_id}")

            return CustomerPortalResponse(portal_url=session.url)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating portal session: {str(e)}")
            raise

    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
        """Verify Stripe webhook signature and construct event

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header value

        Returns:
            Stripe event dict if valid, None if invalid

        Raises:
            ValueError: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Verified webhook signature for event: {event['type']}")
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            raise
