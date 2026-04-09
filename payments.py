# payments.py
from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
import stripe
import os
from db_initialization import supabase

load_dotenv()

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

router = APIRouter()

@router.post("/premium_payment_1")
async def premium_payment_1(request: Request):
  payload = await request.body()
  sig_header = request.headers.get("stripe-signature")

  try:
    event = stripe.Webhook.construct_event(
      payload, sig_header, STRIPE_WEBHOOK_SECRET
    )
  except Exception:
    raise HTTPException(status_code=400, detail="Invalid signature")

  if event["type"] == "checkout.session.completed":
    session = event["data"]["object"]
    username = session["client_reference_id"]

    if username:
      supabase.table("User_Login_Data").update(
        {"account_tier": "premium"}
      ).eq("username", username).execute()
    else:
      print("WARNING: no client_reference_id in checkout session")

  return {"status": "ok"}