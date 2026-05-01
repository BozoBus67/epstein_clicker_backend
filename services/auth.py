from fastapi import HTTPException, Header

from db.client import supabase

def require_user(authorization: str = Header(...)):
  if not authorization.startswith("Bearer "):
    raise HTTPException(status_code=401, detail="Invalid authorization header")
  token = authorization.removeprefix("Bearer ")
  try:
    result = supabase.auth.get_user(token)
  except Exception:
    raise HTTPException(status_code=401, detail="Invalid or expired token")
  if not result.user:
    raise HTTPException(status_code=401, detail="Invalid or expired token")
  return result.user
