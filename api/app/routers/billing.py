"""
Billing Router

API endpoints for subscription and payment management.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models import User, Subscription, Payment, UsageRecord, PlanType, SubscriptionStatus, PaymentStatus
from ..config import settings
from .auth import get_current_user

import stripe
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# Pydantic schemas
class PlanInfo(BaseModel):
    id: str
    name: str
    name_de: str
    price: int  # in cents
    currency: str = "EUR"
    interval: str = "month"
    features: List[str]
    features_de: List[str]
    limits: dict


class SubscriptionResponse(BaseModel):
    id: str
    plan: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    trial_end: Optional[datetime]
    canceled_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class UsageResponse(BaseModel):
    scans_used: int
    scans_limit: int
    pages_scanned: int
    reports_generated: int
    api_calls: int
    period_start: datetime
    period_end: datetime


class PaymentResponse(BaseModel):
    id: str
    amount: int
    currency: str
    status: str
    description: Optional[str]
    invoice_number: Optional[str]
    invoice_pdf_url: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    items: List[PaymentResponse]
    total: int


class CreateCheckoutSession(BaseModel):
    plan: str = Field(..., description="Plan ID: starter, professional, enterprise")
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionUpdate(BaseModel):
    plan: str = Field(..., description="New plan ID")


# Plan definitions
PLANS = {
    "free": PlanInfo(
        id="free",
        name="Free",
        name_de="Kostenlos",
        price=0,
        features=[
            "5 scans per month",
            "Single page scans",
            "Basic reports",
        ],
        features_de=[
            "5 Scans pro Monat",
            "Einzelseitige Scans",
            "Basis-Berichte",
        ],
        limits={
            "scans_per_month": 5,
            "pages_per_scan": 1,
            "reports": False,
            "api_access": False,
        },
    ),
    "starter": PlanInfo(
        id="starter",
        name="Starter",
        name_de="Starter",
        price=4900,  # 49.00 EUR
        features=[
            "50 scans per month",
            "Up to 25 pages per scan",
            "PDF reports",
            "Email support",
        ],
        features_de=[
            "50 Scans pro Monat",
            "Bis zu 25 Seiten pro Scan",
            "PDF-Berichte",
            "E-Mail-Support",
        ],
        limits={
            "scans_per_month": 50,
            "pages_per_scan": 25,
            "reports": True,
            "api_access": False,
        },
    ),
    "professional": PlanInfo(
        id="professional",
        name="Professional",
        name_de="Professional",
        price=14900,  # 149.00 EUR
        features=[
            "Unlimited scans",
            "Up to 100 pages per scan",
            "White-label reports",
            "API access",
            "Priority support",
        ],
        features_de=[
            "Unbegrenzte Scans",
            "Bis zu 100 Seiten pro Scan",
            "White-Label-Berichte",
            "API-Zugang",
            "Prioritäts-Support",
        ],
        limits={
            "scans_per_month": -1,
            "pages_per_scan": 100,
            "reports": True,
            "api_access": True,
        },
    ),
    "agency": PlanInfo(
        id="agency",
        name="Agency",
        name_de="Agentur",
        price=29900,  # 299.00 EUR
        features=[
            "Unlimited scans",
            "Up to 1000 pages per scan",
            "White-label reports",
            "API access",
            "Priority support",
            "Multiple team members",
        ],
        features_de=[
            "Unbegrenzte Scans",
            "Bis zu 1000 Seiten pro Scan",
            "White-Label-Berichte",
            "API-Zugang",
            "Prioritäts-Support",
            "Mehrere Teammitglieder",
        ],
        limits={
            "scans_per_month": -1,
            "pages_per_scan": 1000,
            "reports": True,
            "api_access": True,
        },
    ),
    "enterprise": PlanInfo(
        id="enterprise",
        name="Enterprise",
        name_de="Enterprise",
        price=0,  # Custom pricing
        features=[
            "Unlimited scans and pages",
            "Up to 5000 pages per scan",
            "Dedicated infrastructure",
            "SLA guarantee",
            "Account manager",
            "Custom integrations",
        ],
        features_de=[
            "Unbegrenzte Scans und Seiten",
            "Bis zu 5000 Seiten pro Scan",
            "Dedizierte Infrastruktur",
            "SLA-Garantie",
            "Account Manager",
            "Individuelle Integrationen",
        ],
        limits={
            "scans_per_month": -1,
            "pages_per_scan": 5000,
            "reports": True,
            "api_access": True,
        },
    ),
}


@router.get("/plans", response_model=List[PlanInfo])
async def get_plans():
    """Get all available subscription plans."""
    return list(PLANS.values())


@router.get("/plans/{plan_id}", response_model=PlanInfo)
async def get_plan(plan_id: str):
    """Get a specific plan by ID."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PLANS[plan_id]


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's subscription."""
    user_id = str(current_user.id)

    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if not subscription:
        # Create free subscription if none exists
        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            plan=PlanType.FREE,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)

    return SubscriptionResponse(
        id=str(subscription.id),
        plan=subscription.plan.value,
        status=subscription.status.value,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        trial_end=subscription.trial_end,
        canceled_at=subscription.canceled_at,
        created_at=subscription.created_at,
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current billing period usage."""
    user_id = str(current_user.id)

    # Get subscription for limits
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    plan_limits = PLANS.get(
        subscription.plan.value if subscription else "free",
        PLANS["free"]
    ).limits

    # Calculate current period
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)

    # Get or create usage record
    usage = db.query(UsageRecord).filter(
        UsageRecord.user_id == user_id,
        UsageRecord.period_start == period_start,
    ).first()

    if not usage:
        usage = UsageRecord(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            scans_count=0,
            pages_scanned=0,
            reports_generated=0,
            api_calls=0,
        )
        db.add(usage)
        db.commit()

    return UsageResponse(
        scans_used=usage.scans_count,
        scans_limit=plan_limits["scans_per_month"],
        pages_scanned=usage.pages_scanned,
        reports_generated=usage.reports_generated,
        api_calls=usage.api_calls,
        period_start=period_start,
        period_end=period_end,
    )


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    data: CreateCheckoutSession,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe checkout session for subscription upgrade."""
    user_id = str(current_user.id)

    if data.plan not in ["starter", "professional"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan. Use 'starter' or 'professional', or contact us for enterprise."
        )

    plan = PLANS[data.plan]

    # In production, this would create a real Stripe checkout session
    # For now, return a mock response
    session_id = f"cs_mock_{uuid.uuid4().hex[:16]}"

    return CheckoutSessionResponse(
        checkout_url=f"{settings.FRONTEND_URL}/checkout?session={session_id}",
        session_id=session_id,
    )


@router.post("/subscription/cancel")
async def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel the current subscription."""
    user_id = str(current_user.id)

    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    if subscription.plan == PlanType.FREE:
        raise HTTPException(status_code=400, detail="Cannot cancel free plan")

    # Cancel at end of billing period
    subscription.status = SubscriptionStatus.CANCELED
    subscription.canceled_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Subscription will be canceled at the end of the billing period"}


@router.post("/subscription/reactivate")
async def reactivate_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reactivate a canceled subscription."""
    user_id = str(current_user.id)

    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    if subscription.status != SubscriptionStatus.CANCELED:
        raise HTTPException(status_code=400, detail="Subscription is not canceled")

    # Check if still in billing period
    if subscription.current_period_end and subscription.current_period_end > datetime.now(timezone.utc):
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.canceled_at = None
        db.commit()
        return {"message": "Subscription reactivated"}

    raise HTTPException(
        status_code=400,
        detail="Subscription has expired. Please create a new subscription."
    )


@router.get("/payments", response_model=PaymentListResponse)
async def get_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get payment history."""
    user_id = str(current_user.id)

    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if not subscription:
        return PaymentListResponse(items=[], total=0)

    payments = db.query(Payment).filter(
        Payment.subscription_id == subscription.id
    ).order_by(Payment.created_at.desc()).all()

    return PaymentListResponse(
        items=[
            PaymentResponse(
                id=str(p.id),
                amount=p.amount,
                currency=p.currency,
                status=p.status.value,
                description=p.description,
                invoice_number=p.invoice_number,
                invoice_pdf_url=p.invoice_pdf_url,
                created_at=p.created_at,
                paid_at=p.paid_at,
            )
            for p in payments
        ],
        total=len(payments),
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhooks with proper signature verification.

    This endpoint receives events from Stripe and updates subscription status accordingly.
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    # Verify webhook secret is configured
    if not settings.stripe_webhook_secret:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    # Verify signature
    if not sig_header:
        logger.warning("Missing Stripe-Signature header in webhook request")
        raise HTTPException(status_code=400, detail="Missing signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError as e:
        logger.warning(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    event_type = event["type"]
    event_data = event["data"]["object"]

    logger.info(f"Processing Stripe webhook event: {event_type}")

    try:
        if event_type == "customer.subscription.created":
            await _handle_subscription_created(db, event_data)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(db, event_data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, event_data)
        elif event_type == "invoice.paid":
            await _handle_invoice_paid(db, event_data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, event_data)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
    except Exception as e:
        logger.error(f"Error processing webhook event {event_type}: {e}")
        raise HTTPException(status_code=500, detail="Error processing webhook")

    return {"status": "received", "event_type": event_type}


async def _handle_subscription_created(db: Session, subscription_data: dict):
    """Handle new subscription creation from Stripe."""
    customer_id = subscription_data.get("customer")
    stripe_sub_id = subscription_data.get("id")
    status = subscription_data.get("status")

    # Find user by stripe customer ID
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        logger.warning(f"No user found for Stripe customer: {customer_id}")
        return

    # Map Stripe plan to our plan type
    plan_id = subscription_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("lookup_key", "free")
    plan_type = _map_stripe_plan(plan_id)

    # Create or update subscription
    subscription = db.query(Subscription).filter(Subscription.user_id == str(user.id)).first()
    if not subscription:
        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=str(user.id),
        )
        db.add(subscription)

    subscription.stripe_subscription_id = stripe_sub_id
    subscription.plan = plan_type
    subscription.status = _map_stripe_status(status)
    subscription.current_period_start = datetime.fromtimestamp(
        subscription_data.get("current_period_start", 0), tz=timezone.utc
    )
    subscription.current_period_end = datetime.fromtimestamp(
        subscription_data.get("current_period_end", 0), tz=timezone.utc
    )

    db.commit()
    logger.info(f"Subscription created for user {user.id}: {plan_type.value}")


async def _handle_subscription_updated(db: Session, subscription_data: dict):
    """Handle subscription updates from Stripe."""
    stripe_sub_id = subscription_data.get("id")
    status = subscription_data.get("status")

    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()

    if not subscription:
        logger.warning(f"No subscription found for Stripe sub: {stripe_sub_id}")
        return

    # Update status
    subscription.status = _map_stripe_status(status)
    subscription.current_period_start = datetime.fromtimestamp(
        subscription_data.get("current_period_start", 0), tz=timezone.utc
    )
    subscription.current_period_end = datetime.fromtimestamp(
        subscription_data.get("current_period_end", 0), tz=timezone.utc
    )

    # Handle cancellation
    if subscription_data.get("cancel_at_period_end"):
        subscription.canceled_at = datetime.now(timezone.utc)

    db.commit()
    logger.info(f"Subscription {stripe_sub_id} updated to status: {status}")


async def _handle_subscription_deleted(db: Session, subscription_data: dict):
    """Handle subscription cancellation/deletion from Stripe."""
    stripe_sub_id = subscription_data.get("id")

    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub_id
    ).first()

    if not subscription:
        logger.warning(f"No subscription found for Stripe sub: {stripe_sub_id}")
        return

    # Downgrade to free plan
    subscription.plan = PlanType.FREE
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.stripe_subscription_id = None
    subscription.canceled_at = datetime.now(timezone.utc)

    db.commit()
    logger.info(f"Subscription {stripe_sub_id} deleted, user downgraded to free")


async def _handle_invoice_paid(db: Session, invoice_data: dict):
    """Handle successful payment from Stripe."""
    customer_id = invoice_data.get("customer")
    subscription_id = invoice_data.get("subscription")
    amount = invoice_data.get("amount_paid", 0)

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        logger.warning(f"No user found for Stripe customer: {customer_id}")
        return

    subscription = db.query(Subscription).filter(
        Subscription.user_id == str(user.id)
    ).first()

    if not subscription:
        return

    # Create payment record
    payment = Payment(
        id=uuid.uuid4(),
        subscription_id=subscription.id,
        amount=amount,
        currency=invoice_data.get("currency", "eur").upper(),
        status=PaymentStatus.SUCCEEDED,
        stripe_payment_id=invoice_data.get("payment_intent"),
        invoice_number=invoice_data.get("number"),
        invoice_pdf_url=invoice_data.get("invoice_pdf"),
        paid_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    db.commit()

    logger.info(f"Payment recorded for user {user.id}: {amount}")


async def _handle_payment_failed(db: Session, invoice_data: dict):
    """Handle failed payment from Stripe."""
    customer_id = invoice_data.get("customer")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    subscription = db.query(Subscription).filter(
        Subscription.user_id == str(user.id)
    ).first()

    if subscription:
        subscription.status = SubscriptionStatus.PAST_DUE
        db.commit()

    logger.warning(f"Payment failed for user {user.id}")


def _map_stripe_plan(lookup_key: str) -> PlanType:
    """Map Stripe price lookup key to our plan type."""
    mapping = {
        "starter": PlanType.STARTER,
        "professional": PlanType.PROFESSIONAL,
        "agency": PlanType.AGENCY,
        "enterprise": PlanType.ENTERPRISE,
    }
    return mapping.get(lookup_key, PlanType.FREE)


def _map_stripe_status(status: str) -> SubscriptionStatus:
    """Map Stripe subscription status to our status."""
    mapping = {
        "active": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "incomplete": SubscriptionStatus.INCOMPLETE,
        "incomplete_expired": SubscriptionStatus.EXPIRED,
        "trialing": SubscriptionStatus.TRIALING,
        "unpaid": SubscriptionStatus.PAST_DUE,
    }
    return mapping.get(status, SubscriptionStatus.ACTIVE)
