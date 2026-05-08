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

  # Idempotency: Stripe retries the webhook if our first response times out,
  # so the same event.id can arrive twice. Skip if we've already credited it
  # — without this, a retry would double-credit the user for one payment.
  already = supabase.table("Stripe_Processed_Events").select("event_id").eq("event_id", event["id"]).execute()
  if already.data:
    return {"status": "already_processed", "event_id": event["id"]}

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

  # Mark the event processed AFTER successful credit. If credit raises mid-
  # flight, we never mark the event, and Stripe's retry can re-attempt cleanly.
  # The opposite order (mark first, credit second) would lose the user's money
  # if the credit failed — current order trades a vanishing-rare double-credit
  # window (credit succeeds, mark fails) for never losing the user's payment.
  supabase.table("Stripe_Processed_Events").insert({"event_id": event["id"]}).execute()

  return {"status": "ok"}
