import os

import stripe
from fastapi import APIRouter, HTTPException, Request

from db.client import supabase

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

router = APIRouter()

@router.post("/stripe_webhook")
async def stripe_webhook(request: Request):
  payload = await request.body()
  sig_header = request.headers.get("stripe-signature")

  try:
    event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
  except Exception:
    raise HTTPException(status_code=400, detail="Invalid signature")

  if event["type"] != "checkout.session.completed":
    return {"status": "ignored", "reason": f"unhandled event type: {event['type']}"}

  session = event["data"]["object"]
  user_id = getattr(session, "client_reference_id", None)
  amount_total = getattr(session, "amount_total", None)

  if not user_id:
    raise HTTPException(status_code=400, detail="Missing client_reference_id")
  if not amount_total:
    raise HTTPException(status_code=400, detail="Missing amount_total")

  tokens = amount_total // 100
  if tokens <= 0:
    raise HTTPException(status_code=400, detail="Invalid token amount")

  pgd = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user_id).single().execute().data["premium_game_data"]
  pgd["tokens"] = pgd["tokens"] + tokens
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user_id).execute()

  return {"status": "ok"}
