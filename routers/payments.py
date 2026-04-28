from fastapi import APIRouter, Request, HTTPException
import stripe
import os
from db.client import supabase

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

router = APIRouter()

@router.post("/premium_payment_1")
async def premium_payment_1(request: Request):
  payload = await request.body()
  sig_header = request.headers.get("stripe-signature")

  try:
    event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
  except Exception:
    raise HTTPException(status_code=400, detail="Invalid signature")

  if event["type"] == "checkout.session.completed":
    session = event["data"]["object"]
    user_id = session["client_reference_id"]

    if user_id:
      pgd = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user_id).single().execute().data["premium_game_data"]
      supabase.table("User_Login_Data").update({"premium_game_data": pgd | {"account_tier": "premium"}}).eq("id", user_id).execute()
    else:
      print("WARNING: no client_reference_id in checkout session")

  return {"status": "ok"}
