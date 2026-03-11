# payment.py
import stripe
from fastapi import HTTPException
from dotenv import load_dotenv
import os

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_IDS = {
    "pic_tease": "price_1xxxxxxxxxxxx",   # create these in Stripe dashboard
    "voice_pack": "price_1xxxxxxxxxxxx",
    "exclusive_set": "price_1xxxxxxxxxxxx",
}

async def create_checkout_session(tip_type: str, session_id: str):
    if tip_type not in PRICE_IDS:
        raise HTTPException(400, "Invalid tip type")

    try:
        checkout = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[tip_type], "quantity": 1}],
            mode="payment",
            success_url="https://yourdomain.com/chat?success=true",
            cancel_url="https://yourdomain.com/chat",
            metadata={
                "session_id": session_id,
                "tip_type": tip_type
            }
        )
        return checkout.url
    except Exception as e:
        raise HTTPException(500, f"Stripe error: {str(e)}")