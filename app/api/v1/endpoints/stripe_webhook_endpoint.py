# app/api/v1/endpoints/stripe_webhook_endpoint.py
from fastapi import APIRouter, Request, HTTPException
from app.services.stripe_service import StripeService
from app.services.database_service import DatabaseService
from app.core.stripe_config import calculate_credits
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/webhook")
async def handle_stripe_webhook(request: Request):
    """Handle Stripe webhook events

    This endpoint receives webhook events from Stripe and processes them.
    Currently handles:
    - checkout.session.completed: New subscription created
    - invoice.payment_succeeded: Subscription renewed (reset credits)
    - customer.subscription.updated: Subscription details changed
    - customer.subscription.deleted: Subscription canceled
    - invoice.payment_failed: Payment failed

    Returns:
        Success message

    Raises:
        HTTPException: If webhook verification fails or processing error occurs
    """
    try:
        # Get raw body and signature header
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')

        if not sig_header:
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")

        # Verify webhook signature
        event = StripeService.verify_webhook_signature(payload, sig_header)

        if not event:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        # Process event based on type
        event_type = event['type']
        event_data = event['data']['object']

        logger.info(f"Processing Stripe webhook: {event_type}")

        if event_type == 'checkout.session.completed':
            await handle_checkout_completed(event_data)

        elif event_type == 'invoice.payment_succeeded':
            await handle_payment_succeeded(event_data)

        elif event_type == 'customer.subscription.updated':
            await handle_subscription_updated(event_data)

        elif event_type == 'customer.subscription.deleted':
            await handle_subscription_deleted(event_data)

        elif event_type == 'invoice.payment_failed':
            await handle_payment_failed(event_data)

        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

        return {"status": "success", "event_type": event_type}

    except ValueError as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

async def handle_checkout_completed(session_data: dict):
    """Handle checkout.session.completed event

    Creates subscription record and sets teacher credits.

    Args:
        session_data: Checkout session data from Stripe
    """
    try:
        # Extract metadata
        metadata = session_data.get('metadata', {})
        teacher_id = metadata.get('teacher_id')
        plan_type = metadata.get('plan_type')
        billing_cycle = metadata.get('billing_cycle')
        student_count = int(metadata.get('student_count', 0))

        if not all([teacher_id, plan_type, billing_cycle, student_count]):
            logger.error(f"Missing required metadata in checkout session: {metadata}")
            return

        # Get subscription data
        subscription_id = session_data.get('subscription')
        customer_id = session_data.get('customer')

        if not subscription_id:
            logger.error(f"No subscription ID in checkout session for teacher {teacher_id}")
            return

        # Retrieve full subscription details from Stripe to get period info
        import stripe
        subscription = stripe.Subscription.retrieve(subscription_id)

        # Get period timestamps from subscription items
        # Note: current_period_start/end are in the subscription_item, not the subscription object
        # Access as dictionary since items is a dict, not an attribute
        subscription_item = subscription['items']['data'][0]
        current_period_start = datetime.fromtimestamp(subscription_item['current_period_start'])
        current_period_end = datetime.fromtimestamp(subscription_item['current_period_end'])
        price_id = subscription_item['price']['id']

        print(f"✅ Retrieved subscription: {subscription['id']}")
        print(f"✅ Period start: {current_period_start}")
        print(f"✅ Period end: {current_period_end}")
        print(f"✅ Price ID: {price_id}")

        # Calculate credits
        credits = calculate_credits(plan_type, student_count)

        # Create subscription record in database
        db_service = DatabaseService()
        subscription_db_id = db_service.create_subscription(
            teacher_id=teacher_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            stripe_price_id=price_id,
            plan_type=plan_type,
            billing_cycle=billing_cycle,
            student_count=student_count,
            current_period_start=current_period_start,
            current_period_end=current_period_end
        )

        if not subscription_db_id:
            logger.error(f"Failed to create subscription record for teacher {teacher_id}")
            return

        # Update teacher credits
        success = db_service.update_teacher_credits(teacher_id, credits)

        if success:
            # Also update tier to 'paid'
            db_service.supabase.table('users').update({'tier': 'paid'}).eq('id', teacher_id).execute()
            print(f"✅ Updated teacher {teacher_id} tier to 'paid'")

            logger.info(
                f"✅ Checkout completed for teacher {teacher_id}: "
                f"{plan_type} {billing_cycle} × {student_count} students = {credits} hours"
            )
        else:
            logger.error(f"Failed to update credits for teacher {teacher_id}")

    except Exception as e:
        logger.error(f"Error handling checkout completed: {str(e)}")
        raise

async def handle_payment_succeeded(invoice_data: dict):
    """Handle invoice.payment_succeeded event

    Resets teacher credits on successful renewal payment.

    Args:
        invoice_data: Invoice data from Stripe
    """
    try:
        # Get subscription info from invoice
        subscription_id = invoice_data.get('subscription')

        if not subscription_id:
            logger.info("Invoice not associated with subscription, skipping")
            return

        # Retrieve subscription to get metadata
        import stripe
        subscription = stripe.Subscription.retrieve(subscription_id)

        metadata = subscription.get('metadata', {})
        teacher_id = metadata.get('teacher_id')
        plan_type = metadata.get('plan_type')
        student_count = int(metadata.get('student_count', 0))

        if not all([teacher_id, plan_type, student_count]):
            logger.error(f"Missing required metadata in subscription: {metadata}")
            return

        # Calculate and reset credits
        credits = calculate_credits(plan_type, student_count)

        db_service = DatabaseService()
        success = db_service.update_teacher_credits(teacher_id, credits)

        if success:
            logger.info(
                f"✅ Payment succeeded - Reset credits for teacher {teacher_id}: "
                f"{credits} hours ({plan_type} × {student_count} students)"
            )

            # Update billing period in subscription record
            current_period_start = datetime.fromtimestamp(subscription.current_period_start)
            current_period_end = datetime.fromtimestamp(subscription.current_period_end)

            db_service.update_subscription(
                teacher_id=teacher_id,
                updates={
                    'current_period_start': current_period_start.isoformat(),
                    'current_period_end': current_period_end.isoformat(),
                    'status': 'active'
                }
            )
        else:
            logger.error(f"Failed to reset credits for teacher {teacher_id}")

    except Exception as e:
        logger.error(f"Error handling payment succeeded: {str(e)}")
        raise

async def handle_subscription_updated(subscription_data: dict):
    """Handle customer.subscription.updated event

    Updates subscription details and recalculates credits if quantity changed.

    Args:
        subscription_data: Subscription data from Stripe
    """
    try:
        metadata = subscription_data.get('metadata', {})
        teacher_id = metadata.get('teacher_id')

        if not teacher_id:
            logger.error("Missing teacher_id in subscription metadata")
            return

        # Get current quantity from subscription
        items = subscription_data.get('items', {}).get('data', [])
        if not items:
            logger.error("No items found in subscription")
            return

        new_quantity = items[0].get('quantity', 0)
        plan_type = metadata.get('plan_type')
        status = subscription_data.get('status')

        if not plan_type:
            logger.error("Missing plan_type in subscription metadata")
            return

        # Calculate new credits
        new_credits = calculate_credits(plan_type, new_quantity)

        # Update database
        db_service = DatabaseService()

        # Update subscription record
        current_period_start = datetime.fromtimestamp(subscription_data.get('current_period_start'))
        current_period_end = datetime.fromtimestamp(subscription_data.get('current_period_end'))

        db_service.update_subscription(
            teacher_id=teacher_id,
            updates={
                'student_count': new_quantity,
                'status': status,
                'current_period_start': current_period_start.isoformat(),
                'current_period_end': current_period_end.isoformat()
            }
        )

        # Update credits
        db_service.update_teacher_credits(teacher_id, new_credits)

        logger.info(
            f"✅ Subscription updated for teacher {teacher_id}: "
            f"new quantity={new_quantity}, new credits={new_credits} hours, status={status}"
        )

    except Exception as e:
        logger.error(f"Error handling subscription updated: {str(e)}")
        raise

async def handle_subscription_deleted(subscription_data: dict):
    """Handle customer.subscription.deleted event

    Deletes subscription record and resets teacher to free tier.

    Args:
        subscription_data: Subscription data from Stripe
    """
    try:
        metadata = subscription_data.get('metadata', {})
        teacher_id = metadata.get('teacher_id')

        if not teacher_id:
            logger.error("Missing teacher_id in subscription metadata")
            return

        db_service = DatabaseService()

        # Delete subscription record
        db_service.delete_subscription(teacher_id)

        # Reset to free tier credits (40 hours)
        db_service.update_teacher_credits(teacher_id, 40.0)

        # Update tier back to 'free'
        db_service.supabase.table('users').update({'tier': 'free'}).eq('id', teacher_id).execute()
        print(f"✅ Updated teacher {teacher_id} tier to 'free'")

        logger.info(f"✅ Subscription deleted for teacher {teacher_id} - Reset to free tier")

    except Exception as e:
        logger.error(f"Error handling subscription deleted: {str(e)}")
        raise

async def handle_payment_failed(invoice_data: dict):
    """Handle invoice.payment_failed event

    Updates subscription status to indicate payment failure.

    Args:
        invoice_data: Invoice data from Stripe
    """
    try:
        # Get subscription info from invoice
        subscription_id = invoice_data.get('subscription')

        if not subscription_id:
            logger.info("Invoice not associated with subscription, skipping")
            return

        # Retrieve subscription to get metadata
        import stripe
        subscription = stripe.Subscription.retrieve(subscription_id)

        metadata = subscription.get('metadata', {})
        teacher_id = metadata.get('teacher_id')

        if not teacher_id:
            logger.error("Missing teacher_id in subscription metadata")
            return

        # Update subscription status
        db_service = DatabaseService()
        db_service.update_subscription(
            teacher_id=teacher_id,
            updates={'status': 'past_due'}
        )

        logger.warning(f"⚠️ Payment failed for teacher {teacher_id} - Status updated to past_due")

    except Exception as e:
        logger.error(f"Error handling payment failed: {str(e)}")
        raise
