# app/api/v1/endpoints/stripe_endpoint.py
from fastapi import APIRouter, Depends, HTTPException, Request
from app.models.stripe_model import (
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionInfo,
    UpdateQuantityRequest,
    UpdateQuantityResponse,
    CancelSubscriptionRequest,
    CancelSubscriptionResponse,
    CustomerPortalRequest,
    CustomerPortalResponse
)
from app.services.stripe_service import StripeService
from app.services.database_service import DatabaseService
from app.core.stripe_config import calculate_credits
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_stripe_service():
    return StripeService()

def get_database_service():
    return DatabaseService()

@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: Request,
    checkout_request: CheckoutRequest,
    stripe_service: StripeService = Depends(get_stripe_service)
):
    """Create a Stripe checkout session for subscription purchase

    This endpoint creates a Stripe checkout session for a teacher to purchase
    a subscription plan. The teacher selects a plan (30min/60min), billing cycle
    (monthly/quarterly), and number of students.

    Args:
        checkout_request: Checkout request with plan details

    Returns:
        CheckoutResponse with Stripe checkout URL

    Raises:
        HTTPException: If checkout session creation fails
    """
    try:
        # Get base URL from request
        base_url = str(request.base_url).rstrip('/')

        # Create checkout session
        response = await stripe_service.create_checkout_session(
            request=checkout_request,
            base_url=base_url
        )

        return response

    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")

@router.get("/subscription/{teacher_id}", response_model=SubscriptionInfo)
async def get_subscription(
    teacher_id: str,
    db_service: DatabaseService = Depends(get_database_service)
):
    """Get current subscription information for a teacher

    Args:
        teacher_id: Teacher's user ID

    Returns:
        SubscriptionInfo with current subscription details

    Raises:
        HTTPException: If subscription not found or error occurs
    """
    try:
        # Get subscription from database
        subscription = db_service.get_subscription_by_teacher_id(teacher_id)

        if not subscription:
            # Return empty subscription info if no subscription exists
            return SubscriptionInfo(teacher_id=teacher_id)

        # Get teacher's current credits
        teacher = db_service.supabase.table('users').select('credits').eq('id', teacher_id).execute()
        credits = teacher.data[0].get('credits') if teacher.data else None

        return SubscriptionInfo(
            teacher_id=teacher_id,
            plan_type=subscription.get('plan_type'),
            billing_cycle=subscription.get('billing_cycle'),
            student_count=subscription.get('student_count'),
            credits=credits,
            status=subscription.get('status'),
            current_period_start=subscription.get('current_period_start'),
            current_period_end=subscription.get('current_period_end'),
            stripe_customer_id=subscription.get('stripe_customer_id'),
            stripe_subscription_id=subscription.get('stripe_subscription_id'),
            created_at=subscription.get('created_at')
        )

    except Exception as e:
        logger.error(f"Error fetching subscription for teacher {teacher_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch subscription: {str(e)}")

@router.post("/update-quantity", response_model=UpdateQuantityResponse)
async def update_quantity(
    update_request: UpdateQuantityRequest,
    stripe_service: StripeService = Depends(get_stripe_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Update student count for an existing subscription

    This will update the subscription quantity in Stripe and recalculate credits.
    Stripe will automatically prorate the charges.

    Args:
        update_request: Request with new student count

    Returns:
        UpdateQuantityResponse with success status and new credits

    Raises:
        HTTPException: If subscription not found or update fails
    """
    try:
        # Get existing subscription
        subscription = db_service.get_subscription_by_teacher_id(update_request.teacher_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Update in Stripe
        response = await stripe_service.update_subscription_quantity(
            request=update_request,
            stripe_subscription_id=subscription['stripe_subscription_id'],
            plan_type=subscription['plan_type']
        )

        if not response.success:
            return response

        # Update in database
        db_service.update_subscription(
            teacher_id=update_request.teacher_id,
            updates={'student_count': update_request.new_student_count}
        )

        # Update teacher credits
        db_service.update_teacher_credits(
            teacher_id=update_request.teacher_id,
            credits=response.new_credits
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription quantity: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update quantity: {str(e)}")

@router.post("/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    cancel_request: CancelSubscriptionRequest,
    stripe_service: StripeService = Depends(get_stripe_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Cancel a subscription

    Args:
        cancel_request: Cancellation request

    Returns:
        CancelSubscriptionResponse with success status

    Raises:
        HTTPException: If subscription not found or cancellation fails
    """
    try:
        # Get existing subscription
        subscription = db_service.get_subscription_by_teacher_id(cancel_request.teacher_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Cancel in Stripe
        response = await stripe_service.cancel_subscription(
            request=cancel_request,
            stripe_subscription_id=subscription['stripe_subscription_id']
        )

        if not response.success:
            return response

        # Update status in database
        if cancel_request.cancel_at_period_end:
            db_service.update_subscription(
                teacher_id=cancel_request.teacher_id,
                updates={'status': 'canceling'}
            )
        else:
            # Delete subscription record for immediate cancellation
            db_service.delete_subscription(cancel_request.teacher_id)
            # Reset credits to default free tier
            db_service.update_teacher_credits(cancel_request.teacher_id, 40.0)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {str(e)}")

@router.post("/customer-portal", response_model=CustomerPortalResponse)
async def create_customer_portal(
    portal_request: CustomerPortalRequest,
    request: Request,
    stripe_service: StripeService = Depends(get_stripe_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Create a Stripe customer portal session

    The customer portal allows teachers to manage their subscription,
    update payment methods, view invoices, etc.

    Args:
        portal_request: Portal request with teacher ID

    Returns:
        CustomerPortalResponse with portal URL

    Raises:
        HTTPException: If subscription not found or portal creation fails
    """
    try:
        # Get existing subscription
        subscription = db_service.get_subscription_by_teacher_id(portal_request.teacher_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Get base URL from request
        base_url = str(request.base_url).rstrip('/')

        # Create portal session
        response = await stripe_service.create_customer_portal_session(
            request=portal_request,
            stripe_customer_id=subscription['stripe_customer_id'],
            base_url=base_url
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating customer portal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create portal: {str(e)}")
