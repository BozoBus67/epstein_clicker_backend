from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db.client import supabase
from services.auth import require_user
from services.cookies import add_cookies, spend_cookies
from services.tokens import add_tokens, spend_tokens

router = APIRouter()

class CreateListingRequest(BaseModel):
  listing_type: Literal["tokens", "cookies"]
  amount: int
  price_type: Literal["tokens", "cookies"]
  price: int

class ListingRequest(BaseModel):
  listing_id: str

@router.post("/create_listing")
def create_listing(body: CreateListingRequest, user=Depends(require_user)):
  if body.amount <= 0 or body.price <= 0:
    raise HTTPException(status_code=400, detail="Amount and price must be positive")

  if body.listing_type == "tokens":
    spend_tokens(user.id, body.amount)
  elif body.listing_type == "cookies":
    spend_cookies(user.id, body.amount)

  user_row = supabase.table("User_Login_Data").select("username").eq("id", user.id).single().execute()
  username = user_row.data["username"]

  result = supabase.table("Auction_House").insert({
    "seller_username": username,
    "selling_item_type": body.listing_type,
    "amount": body.amount,
    "price_item_type": body.price_type,
    "price_item_amount": body.price,
    "creation_timestamptz": datetime.now(timezone.utc).isoformat(),
  }).execute()

  pgd_result = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute()
  return {"status": "ok", "listing": result.data[0], "premium_game_data": pgd_result.data["premium_game_data"]}

@router.get("/get_listings")
def get_listings():
  result = supabase.table("Auction_House").select("*").execute()
  return result.data

@router.post("/buy_listing")
def buy_listing(body: ListingRequest, user=Depends(require_user)):
  listing_result = supabase.table("Auction_House").select("*").eq("id", body.listing_id).single().execute()
  if not listing_result.data:
    raise HTTPException(status_code=404, detail="Listing not found")
  listing = listing_result.data

  seller_row = supabase.table("User_Login_Data").select("id").eq("username", listing["seller_username"]).single().execute()
  seller_id = seller_row.data["id"]

  if str(user.id) == str(seller_id):
    raise HTTPException(status_code=400, detail="Cannot buy your own listing")

  if listing["price_item_type"] == "tokens":
    spend_tokens(user.id, listing["price_item_amount"])
    add_tokens(seller_id, listing["price_item_amount"])
  elif listing["price_item_type"] == "cookies":
    spend_cookies(user.id, listing["price_item_amount"])
    add_cookies(seller_id, listing["price_item_amount"])

  if listing["selling_item_type"] == "tokens":
    add_tokens(user.id, listing["amount"])
  elif listing["selling_item_type"] == "cookies":
    add_cookies(user.id, listing["amount"])

  supabase.table("Auction_House").delete().eq("id", body.listing_id).execute()

  buyer_data = supabase.table("User_Login_Data").select("game_data, premium_game_data").eq("id", user.id).single().execute().data
  return {"status": "ok", "listing": listing, "game_data": buyer_data["game_data"], "premium_game_data": buyer_data["premium_game_data"]}

@router.post("/cancel_listing")
def cancel_listing(body: ListingRequest, user=Depends(require_user)):
  listing_result = supabase.table("Auction_House").select("*").eq("id", body.listing_id).single().execute()
  if not listing_result.data:
    raise HTTPException(status_code=404, detail="Listing not found")
  listing = listing_result.data

  user_row = supabase.table("User_Login_Data").select("username").eq("id", user.id).single().execute()
  if user_row.data["username"] != listing["seller_username"]:
    raise HTTPException(status_code=403, detail="You don't own this listing")

  if listing["selling_item_type"] == "tokens":
    add_tokens(user.id, listing["amount"])
  elif listing["selling_item_type"] == "cookies":
    add_cookies(user.id, listing["amount"])

  supabase.table("Auction_House").delete().eq("id", body.listing_id).execute()

  user_data = supabase.table("User_Login_Data").select("game_data, premium_game_data").eq("id", user.id).single().execute().data
  return {"status": "ok", "listing": listing, "game_data": user_data["game_data"], "premium_game_data": user_data["premium_game_data"]}
