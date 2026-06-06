import os
import stripe
from services.auth_service import set_user_pro


def _get_stripe():
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    return stripe


def create_checkout_session(user_id: str, user_email: str, plan: str) -> str:
    s = _get_stripe()
    price_map = {
        "monthly": os.environ.get("STRIPE_PRICE_MONTHLY"),
        "annual":  os.environ.get("STRIPE_PRICE_ANNUAL"),
    }
    price_id = price_map.get(plan)
    if not price_id:
        raise ValueError(f"Unknown plan '{plan}'. Expected 'monthly' or 'annual'.")

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    session = s.checkout.Session.create(
        customer_email=user_email,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{frontend_url}?upgraded=1",
        cancel_url=frontend_url,
        metadata={"user_id": user_id},
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str | None) -> dict:
    s = _get_stripe()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = s.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid Stripe webhook signature")

    evt_type = event["type"]
    data = event["data"]["object"]

    if evt_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id")
        customer_id = data.get("customer")
        if user_id:
            set_user_pro(user_id, True, customer_id)

    elif evt_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        customer_id = data.get("customer")
        if customer_id:
            # Look up user by stripe_customer_id
            from services.auth_service import _sb
            try:
                res = _sb().table("users").select("id").eq("stripe_customer_id", customer_id).single().execute()
                if res.data:
                    set_user_pro(res.data["id"], False)
            except Exception:
                pass

    return {"received": True}
