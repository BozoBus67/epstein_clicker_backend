import os

from supabase import create_client, ClientOptions

supabase = create_client(
  os.getenv("SUPABASE_URL"),
  os.getenv("SUPABASE_SECRET_KEY"),
  options=ClientOptions(
    auto_refresh_token=False,
    persist_session=False,
  )
)
