"""
Billing Router

API endpoints for subscription and payment management.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models import User, Subscription, Payment, UsageRecord, PlanType, SubscriptionStatus, PaymentStatus
from ..config import settings
from .auth import get_current_user

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
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
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
    now = datetime.utcnow()
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
    subscription.canceled_at = datetime.utcnow()
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
    if subscription.current_period_end and subscription.current_period_end > datetime.utcnow():
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
    """Handle Stripe webhooks."""
    # In production, verify webhook signature
    payload = await request.body()

    # Process webhook events
    # This is a placeholder - implement actual Stripe webhook handling

    return {"status": "received"}
