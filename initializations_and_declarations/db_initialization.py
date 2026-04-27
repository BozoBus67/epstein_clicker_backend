# db.py
import os
from supabase import create_client
from supabase.lib.client_options import ClientOptions

supabase = create_client(
  os.getenv("SUPABASE_URL"),
  os.getenv("SUPABASE_SERVICE_KEY"),
  options=ClientOptions(auto_refresh_token=False, persist_session=False)
)
