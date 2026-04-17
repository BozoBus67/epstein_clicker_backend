from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from initializations_and_declarations.db_initialization import supabase
from utils import migrate_game_data

router = APIRouter()

INVALID_CREDENTIALS = "Incorrect username, email, or password"

class LoginRequest(BaseModel):
  username_or_email: str
  password: str

@router.post("/login")
def login(body: LoginRequest):
  # first try input directly as an email
  # if it's not an email or doesn't exist, supabase throws — fall through to username path
  try:
    auth_result = supabase.auth.sign_in_with_password({
      "email": body.username_or_email,
      "password": body.password,
    })
  except Exception:

    # look up the username in our table to get the uuid
    row = supabase.table("User_Login_Data").select("id").eq(
      "username", body.username_or_email
    ).execute()
    if not row.data:
      raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)

    # use the uuid to get the email from supabase auth
    # this can fail if the account predates the auth migration
    try:
      auth_user = supabase.auth.admin.get_user_by_id(row.data[0]["id"])
      if not auth_user.user:
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)
      email = auth_user.user.email
    except HTTPException:
      raise  # re-raise our own 401, don't swallow it
    except Exception:
      raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)

    # now sign in with the resolved email
    try:
      auth_result = supabase.auth.sign_in_with_password({
        "email": email,
        "password": body.password,
      })
    except Exception:
      raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)

  user_id = auth_result.user.id
  jwt = auth_result.session.access_token

  # fetch game data from our table using the verified uuid
  result = supabase.table("User_Login_Data").select(
    "id, username, game_data, premium_game_data"
  ).eq("id", user_id).execute()

  if not result.data:
    raise HTTPException(status_code=404, detail="Account data not found")

  user = result.data[0]
  user["game_data"] = migrate_game_data(user["game_data"])

  return {
    "status": "ok",
    "jwt": jwt,
    "user": user,
  }