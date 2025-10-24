# app/models/stripe_model.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class CheckoutRequest(BaseModel):
    """Request to create a Stripe checkout session"""
    plan_type: str = Field(..., description="Plan type: '30min' or '60min'")
    billing_cycle: str = Field(..., description="Billing cycle: 'monthly' or 'quarterly'")
    student_count: int = Field(..., gt=0, description="Number of students (must be > 0)")
    teacher_id: str = Field(..., description="Teacher's user ID")
    success_url: Optional[str] = Field(None, description="URL to redirect after successful payment")
    cancel_url: Optional[str] = Field(None, description="URL to redirect if payment is canceled")

    @field_validator('plan_type')
    @classmethod
    def validate_plan_type(cls, v):
        if v not in ['30min', '60min']:
            raise ValueError("plan_type must be '30min' or '60min'")
        return v

    @field_validator('billing_cycle')
    @classmethod
    def validate_billing_cycle(cls, v):
        if v not in ['monthly', 'quarterly']:
            raise ValueError("billing_cycle must be 'monthly' or 'quarterly'")
        return v

class CheckoutResponse(BaseModel):
    """Response containing Stripe checkout session URL"""
    checkout_url: str = Field(..., description="Stripe checkout session URL")
    session_id: str = Field(..., description="Stripe checkout session ID")

class SubscriptionInfo(BaseModel):
    """Current subscription information for a teacher"""
    teacher_id: str
    plan_type: Optional[str] = None
    billing_cycle: Optional[str] = None
    student_count: Optional[int] = None
    credits: Optional[float] = None
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: Optional[datetime] = None

class UpdateQuantityRequest(BaseModel):
    """Request to update student count for an existing subscription"""
    teacher_id: str = Field(..., description="Teacher's user ID")
    new_student_count: int = Field(..., gt=0, description="New number of students")

class UpdateQuantityResponse(BaseModel):
    """Response after updating subscription quantity"""
    success: bool
    message: str
    new_credits: Optional[float] = None

class CancelSubscriptionRequest(BaseModel):
    """Request to cancel a subscription"""
    teacher_id: str = Field(..., description="Teacher's user ID")
    cancel_at_period_end: bool = Field(
        True,
        description="If True, cancel at end of billing period. If False, cancel immediately."
    )

class CancelSubscriptionResponse(BaseModel):
    """Response after canceling subscription"""
    success: bool
    message: str
    canceled_at: Optional[datetime] = None

class CustomerPortalRequest(BaseModel):
    """Request to create Stripe customer portal session"""
    teacher_id: str = Field(..., description="Teacher's user ID")
    return_url: Optional[str] = Field(None, description="URL to return to after portal session")

class CustomerPortalResponse(BaseModel):
    """Response containing customer portal URL"""
    portal_url: str = Field(..., description="Stripe customer portal URL")

class WebhookEvent(BaseModel):
    """Stripe webhook event data"""
    event_type: str
    event_id: str
    data: dict
