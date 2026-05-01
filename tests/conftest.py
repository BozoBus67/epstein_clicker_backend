import os

# db.client builds a Supabase client at module-load time using these env vars.
# Tests don't make real network calls (every test patches `supabase` with a
# fake), but the env vars still need to be present so the import succeeds.
os.environ.setdefault("SUPABASE_URL", "http://test-supabase.local")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("STRIPE_SECRET_KEY", "test-stripe-key")
