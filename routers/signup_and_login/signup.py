import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client, ClientOptions
from supabase_auth.errors import AuthApiError, AuthWeakPasswordError

from data.game_data import INITIAL_GAME_DATA
from data.premium_game_data import INITIAL_PREMIUM_GAME_DATA
from db.client import supabase

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
# Optional. Comma-separated list of Discord user IDs to ping on each signup
# (e.g. "12345,67890"). Each id gets a real push notification instead of a
# silent channel post. Get an id via Discord → User Settings → Advanced →
# enable Developer Mode → right-click a username → Copy User ID. Leave the
# env var unset (or empty) to skip pings entirely.
DISCORD_PING_USER_IDS = [
  uid.strip() for uid in os.getenv("DISCORD_PING_USER_IDS", "").split(",") if uid.strip()
]

def notify_discord_signup(username: str, email: str):
  ping_prefix = "".join(f"<@{uid}> " for uid in DISCORD_PING_USER_IDS)
  payload = {"content": f"{ping_prefix}New signup: **{username}** ({email})"}
  if DISCORD_PING_USER_IDS:
    # Webhook mentions are silent by default — Discord requires each user id
    # to also appear in `allowed_mentions.users` for the ping to actually
    # deliver as a notification. Without this the `<@id>` renders as plain
    # text in the channel.
    payload["allowed_mentions"] = {"users": DISCORD_PING_USER_IDS}
  try:
    res = httpx.post(DISCORD_WEBHOOK_URL, json=payload)
    print(f"[discord] status={res.status_code} body={res.text}")
  except Exception as e:
    print(f"[discord] error: {e}")

router = APIRouter()

class SignUpRequest(BaseModel):
  email: str
  username: str
  password: str

@router.post("/signup")
def signup(body: SignUpRequest):
  # Step 1: create user in Supabase auth (email_confirm=True skips email verification).
  # Supabase exposes typed exception classes with structured `.code` and `.status`,
  # so we match on those rather than substring-matching the human-readable message.
  try:
    auth_result = supabase.auth.admin.create_user({
      "email": body.email,
      "password": body.password,
      "email_confirm": True,
    })
  except AuthWeakPasswordError as e:
    raise HTTPException(status_code=400, detail=f"Weak password: {'; '.join(e.reasons)}")
  except AuthApiError as e:
    print(f"[signup] create_user error: code={e.code} status={e.status} message={e.message}")
    if e.code in ("email_exists", "user_already_exists"):
      raise HTTPException(status_code=409, detail="Email already registered")
    if e.code == "email_address_invalid":
      raise HTTPException(status_code=400, detail="Invalid email address")
    if e.code == "over_email_send_rate_limit":
      raise HTTPException(status_code=429, detail="Too many signup attempts — try again later")
    raise HTTPException(status_code=e.status or 500, detail=e.message)

  user_id = auth_result.user.id

  # Step 2: insert game data row — if this fails, delete the auth user to keep things consistent
  try:
    supabase.table("User_Login_Data").insert({
      "id": user_id,
      "username": body.username,
      "game_data": INITIAL_GAME_DATA,
      "premium_game_data": INITIAL_PREMIUM_GAME_DATA,
    }).execute()
  except Exception as e:
    print(f"[signup] User_Login_Data insert error: {e}")
    supabase.auth.admin.delete_user(user_id)  # rollback auth user
    msg = str(e).lower()
    if "duplicate" in msg or "unique" in msg:
      raise HTTPException(status_code=409, detail="Username already taken")
    raise HTTPException(status_code=500, detail=f"Failed to save account data: {e}")

  # Step 3: auto-login so the user lands in the game immediately after signup
  try:
    login_client = create_client(
      os.getenv("SUPABASE_URL"),
      os.getenv("SUPABASE_SECRET_KEY"),
      options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )
    auth_result = login_client.auth.sign_in_with_password({"email": body.email, "password": body.password})
  except Exception as e:
    print(f"[signup] post-signup sign_in error: {e}")
    raise HTTPException(status_code=500, detail=f"Account created but auto-login failed: {e}")

  notify_discord_signup(body.username, body.email)

  return {
    "status": "ok",
    "jwt": auth_result.session.access_token,
    "refresh_token": auth_result.session.refresh_token,
    "user": {
      "id": user_id,
      "username": body.username,
      "email": body.email,
      "game_data": INITIAL_GAME_DATA,
      "premium_game_data": INITIAL_PREMIUM_GAME_DATA,
    },
  }
