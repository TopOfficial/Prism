import os
import json
import stripe
from services.auth_service import grant_from_stripe, set_subscriber, _sb

# Credit packs: each maps to its own Stripe one-time price ID + how many credits it grants.
PACKS = {
    "starter":  {"env": "STRIPE_PRICE_STARTER",  "credits": 5},
    "standard": {"env": "STRIPE_PRICE_STANDARD", "credits": 15},
    "pro":      {"env": "STRIPE_PRICE_PRO",       "credits": 40},
}


def _get_stripe():
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    return stripe


def create_checkout_session(user_id: str, user_email: str, plan: str, quantity: int = 1) -> str:
    """
    plan:
      - "subscription"           → recurring $14.99/mo, unlimited research
      - "starter"|"standard"|"pro" → one-time credit pack
      - "credits"                → custom one-time purchase, `quantity` credits at $0.99 each
    """
    s = _get_stripe()
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")

    if plan == "subscription":
        price_id = os.environ.get("STRIPE_PRICE_SUBSCRIPTION")
        if not price_id:
            raise ValueError("STRIPE_PRICE_SUBSCRIPTION is not configured")
        session = s.checkout.Session.create(
            customer_email=user_email,
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{frontend_url}?purchased=1",
            cancel_url=frontend_url,
            metadata={"user_id": user_id, "kind": "subscription"},
        )
        return session.url

    if plan in PACKS:
        pack = PACKS[plan]
        price_id = os.environ.get(pack["env"])
        if not price_id:
            raise ValueError(f"{pack['env']} is not configured")
        session = s.checkout.Session.create(
            customer_email=user_email,
            line_items=[{"price": price_id, "quantity": 1}],
            mode="payment",
            success_url=f"{frontend_url}?purchased=1",
            cancel_url=frontend_url,
            # Stripe emails a payment receipt to this address on success.
            payment_intent_data={"receipt_email": user_email},
            metadata={"user_id": user_id, "kind": "credits", "credits": str(pack["credits"])},
        )
        return session.url

    if plan == "credits":
        price_id = os.environ.get("STRIPE_PRICE_CREDIT")  # $0.99 per unit
        if not price_id:
            raise ValueError("STRIPE_PRICE_CREDIT is not configured")
        qty = max(1, min(int(quantity), 999))
        session = s.checkout.Session.create(
            customer_email=user_email,
            line_items=[{"price": price_id, "quantity": qty}],
            mode="payment",
            success_url=f"{frontend_url}?purchased=1",
            cancel_url=frontend_url,
            # Stripe emails a payment receipt to this address on success.
            payment_intent_data={"receipt_email": user_email},
            metadata={"user_id": user_id, "kind": "credits", "credits": str(qty)},
        )
        return session.url

    raise ValueError(f"Unknown plan '{plan}'.")


def create_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe Billing (Customer) Portal session so the user can manage/cancel their
    subscription, update payment method, and view invoices. Returns the portal URL."""
    s = _get_stripe()
    session = s.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url


def cancel_customer_subscriptions(customer_id: str) -> None:
    """Cancel all active subscriptions for a Stripe customer — used on account deletion so a
    removed account can't keep getting billed. Best-effort; logs and swallows errors."""
    if not customer_id:
        return
    try:
        s = _get_stripe()
        subs = s.Subscription.list(customer=customer_id, status="active", limit=100)
        for sub in subs.auto_paging_iter():
            try:
                s.Subscription.cancel(sub.id)
                print(f"[STRIPE] cancelled subscription {sub.id} for {customer_id}")
            except Exception as e:
                print(f"[STRIPE] cancel sub {sub.id} failed: {e}")
    except Exception as e:
        print(f"[STRIPE] cancel_customer_subscriptions failed for {customer_id}: {e}")


def handle_webhook(payload: bytes, sig_header: str | None) -> dict:
    s = _get_stripe()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        s.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid Stripe webhook signature")

    # Signature verified — parse the raw payload as plain dicts. (Stripe's StripeObject
    # doesn't expose .get() as a dict method in this version, so avoid it entirely.)
    event = json.loads(payload)
    evt_type = event["type"]
    data = event["data"]["object"]
    print(f"[STRIPE] webhook received: {evt_type}")

    if evt_type == "checkout.session.completed":
        meta = data.get("metadata") or {}
        user_id = meta.get("user_id")
        kind = meta.get("kind")
        customer_id = data.get("customer")
        print(f"[STRIPE] checkout.session.completed user_id={user_id} kind={kind} credits={meta.get('credits')}")
        if not user_id or kind not in ("subscription", "credits"):
            # Can't be fixed by retrying — log and acknowledge so Stripe stops resending.
            print(f"[STRIPE] WARNING: nothing to grant (user_id={user_id}, kind={kind})")
        else:
            try:
                credits = int(meta.get("credits") or 0)
            except (TypeError, ValueError):
                credits = 0
            # Atomic + idempotent. Raises on failure → 5xx → Stripe retries safely.
            grant_from_stripe(event["id"], user_id, kind, credits, customer_id)

    elif evt_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        customer_id = data.get("customer")
        if customer_id:
            try:
                res = _sb().table("users").select("id").eq("stripe_customer_id", customer_id).single().execute()
                if res.data:
                    set_subscriber(res.data["id"], False)
            except Exception:
                pass

    return {"received": True}
