from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from utils import require_user
from db_initialization import supabase

router = APIRouter()

class CreateListingRequest(BaseModel):
  username: str
  listing_type: Literal["tokens", "cookies"]
  amount: int
  price: int

class ListingRequest(BaseModel):
  username: str
  listing_id: str

@router.post("/create_listing")
def create_listing(body: CreateListingRequest):
  user = require_user(body.username)

  if body.listing_type == "tokens":
    balance = user["premium_tokens"]
    if balance < body.amount:
      raise HTTPException(status_code=400, detail="Not enough tokens")
    supabase.table("User_Login_Data").update({
      "premium_tokens": balance - body.amount
    }).eq("username", body.username).execute()

  else:
    balance = user["game_data"]["cookies"]
    if balance < body.amount:
      raise HTTPException(status_code=400, detail="Not enough cookies")
    supabase.table("User_Login_Data").update({
      "game_data": {**user["game_data"], "cookies": balance - body.amount}
    }).eq("username", body.username).execute()

  supabase.table("Auction_House").insert({
    "seller_username": body.username,
    "listing_type": body.listing_type,
    "amount": body.amount,
    "price": body.price
  }).execute()

  return {"status": "ok"}

@router.get("/get_listings")
def get_listings():
  result = supabase.table("Auction_House").select("*").execute()
  return result.data

@router.post("/buy_listing")
def buy_listing(body: ListingRequest):
  buyer = require_user(body.username)

  listing_result = (supabase.table("Auction_House")
    .select("*")
    .eq("id", body.listing_id)
    .single()
    .execute())
  listing = listing_result.data

  if not listing:
    raise HTTPException(status_code=404, detail="Listing not found")

  if listing["seller_username"] == body.username:
    raise HTTPException(status_code=400, detail="Cannot buy your own listing")

  seller = require_user(listing["seller_username"])

  if listing["listing_type"] == "tokens":
    buyer_cookies = buyer["game_data"]["cookies"]
    if buyer_cookies < listing["price"]:
      raise HTTPException(status_code=400, detail="Not enough cookies")

    supabase.table("User_Login_Data").update({
      "game_data": {**buyer["game_data"], "cookies": buyer_cookies - listing["price"]}
    }).eq("username", body.username).execute()

    supabase.table("User_Login_Data").update({
      "premium_tokens": buyer["premium_tokens"] + listing["amount"]
    }).eq("username", body.username).execute()

    supabase.table("User_Login_Data").update({
      "game_data": {**seller["game_data"], "cookies": seller["game_data"]["cookies"] + listing["price"]}
    }).eq("username", listing["seller_username"]).execute()

  else:
    buyer_tokens = buyer["premium_tokens"]
    if buyer_tokens < listing["price"]:
      raise HTTPException(status_code=400, detail="Not enough tokens")

    supabase.table("User_Login_Data").update({
      "premium_tokens": buyer_tokens - listing["price"]
    }).eq("username", body.username).execute()

    supabase.table("User_Login_Data").update({
      "game_data": {**buyer["game_data"], "cookies": buyer["game_data"]["cookies"] + listing["amount"]}
    }).eq("username", body.username).execute()

    supabase.table("User_Login_Data").update({
      "premium_tokens": seller["premium_tokens"] + listing["price"]
    }).eq("username", listing["seller_username"]).execute()

  supabase.table("Auction_House").delete().eq("id", body.listing_id).execute()

  return {"status": "ok"}

@router.post("/cancel_listing")
def cancel_listing(body: ListingRequest):
  user = require_user(body.username)

  listing_result = (supabase.table("Auction_House")
    .select("*")
    .eq("id", body.listing_id)
    .single()
    .execute())
  listing = listing_result.data
  if not listing:
    raise HTTPException(status_code=404, detail="Listing not found")

  if listing["seller_username"] != body.username:
    raise HTTPException(status_code=403, detail="Not your listing")

  if listing["listing_type"] == "tokens":
    supabase.table("User_Login_Data").update({
      "premium_tokens": user["premium_tokens"] + listing["amount"]
    }).eq("username", body.username).execute()
  else:
    supabase.table("User_Login_Data").update({
      "game_data": {**user["game_data"], "cookies": user["game_data"]["cookies"] + listing["amount"]}
    }).eq("username", body.username).execute()

  supabase.table("Auction_House").delete().eq("id", body.listing_id).execute()

  return {"status": "ok"}