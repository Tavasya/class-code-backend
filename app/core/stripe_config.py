# app/core/stripe_config.py
import os
import stripe
import logging
from dotenv import load_dotenv
from typing import Dict

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Price IDs
STRIPE_PRICE_30MIN_MONTHLY = os.getenv("STRIPE_PRICE_30MIN_MONTHLY")
STRIPE_PRICE_30MIN_QUARTERLY = os.getenv("STRIPE_PRICE_30MIN_QUARTERLY")
STRIPE_PRICE_60MIN_MONTHLY = os.getenv("STRIPE_PRICE_60MIN_MONTHLY")
STRIPE_PRICE_60MIN_QUARTERLY = os.getenv("STRIPE_PRICE_60MIN_QUARTERLY")

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info("Stripe API initialized successfully")
else:
    logger.warning("Stripe API key not found in environment variables")

# Price mapping for easy lookup
PRICE_MAP: Dict[str, Dict[str, str]] = {
    "30min": {
        "monthly": STRIPE_PRICE_30MIN_MONTHLY,
        "quarterly": STRIPE_PRICE_30MIN_QUARTERLY,
    },
    "60min": {
        "monthly": STRIPE_PRICE_60MIN_MONTHLY,
        "quarterly": STRIPE_PRICE_60MIN_QUARTERLY,
    }
}

# Plan minutes for credit calculation
PLAN_MINUTES = {
    "30min": 30,
    "60min": 60
}

def get_price_id(plan_type: str, billing_cycle: str) -> str:
    """Get Stripe price ID for a given plan and billing cycle

    Args:
        plan_type: "30min" or "60min"
        billing_cycle: "monthly" or "quarterly"

    Returns:
        Stripe price ID

    Raises:
        ValueError: If invalid plan_type or billing_cycle
    """
    if plan_type not in PRICE_MAP:
        raise ValueError(f"Invalid plan_type: {plan_type}. Must be '30min' or '60min'")

    if billing_cycle not in PRICE_MAP[plan_type]:
        raise ValueError(f"Invalid billing_cycle: {billing_cycle}. Must be 'monthly' or 'quarterly'")

    return PRICE_MAP[plan_type][billing_cycle]

def calculate_credits(plan_type: str, student_count: int) -> float:
    """Calculate total credits (in hours) for a subscription

    Formula: (plan_minutes × student_count) / 60

    Args:
        plan_type: "30min" or "60min"
        student_count: Number of students

    Returns:
        Total credits in hours

    Example:
        calculate_credits("30min", 25) -> 12.5 hours
        calculate_credits("60min", 10) -> 10.0 hours
    """
    if plan_type not in PLAN_MINUTES:
        raise ValueError(f"Invalid plan_type: {plan_type}")

    if student_count <= 0:
        raise ValueError("student_count must be greater than 0")

    plan_minutes = PLAN_MINUTES[plan_type]
    total_credits = (plan_minutes * student_count) / 60

    logger.info(f"Calculated credits: {plan_type} × {student_count} students = {total_credits} hours")

    return total_credits
