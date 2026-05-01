> ⚠️ AI-generated, not yet proofread by a human. Treat as tech debt.

# Backend

FastAPI service backing the Epstein Clicker frontend. Talks to Supabase (Postgres + auth) and Stripe (purchases). Deployed on Render; the frontend talks to it over HTTPS.

## Fail loud and early

Same rule as the frontend: don't silently swallow problems. If `premium_game_data` is missing a key, raise a clear `HTTPException` so the frontend can surface it — don't paper over with `.get(key, 0)` defaults that hide the migration bug. If a Supabase call returns nothing where a row was expected, raise rather than returning `{"status": "error"}`. If you catch an exception, re-raise it as an `HTTPException` with a useful `detail` string; never swallow.

The one place we deliberately use `.get(key, default)` is `services/migrations.py::ensure_user_data_complete` — that's the *one* function whose job is to reconcile missing keys. Every other endpoint expects the migration to have already run and crashes loud if it hasn't.

## Folder layout

- `main.py` — FastAPI app entry. Loads `.env`, configures Stripe, registers every router, exposes `GET /` for health.
- `routers/` — HTTP endpoints. One file per feature area. Sub-folders for grouped families (`signup_and_login/`, `redeem/`).
- `services/` — non-HTTP business logic shared across routers (auth dependency, token/cookie spend helpers, scroll increments, slot win computation, login-time data migration).
- `data/` — canonical constants and initial-state shapes (`INITIAL_GAME_DATA`, `INITIAL_PREMIUM_GAME_DATA`, `MASTERY_SCROLLS`, `ACCOUNT_TIERS`, `BUILDINGS`).
- `constants/` — magic numbers used across the codebase (slot reel size, alphabet size, account-tier IDs and prices).
- `db/` — the singleton Supabase client used by everything that reads/writes Postgres.
- `tests/` — pytest suite. Runs without network: `_fake_supabase.py` is a chainable stub for the supabase client, and `conftest.py` sets dummy env vars so `db/client.py` imports cleanly.
- `scripts/` — one-off migration scripts and dev-convenience scripts (e.g. `give_tokens.py`, `give_floyd_scroll.py` for granting yourself state during local testing). Not imported by the app. Run manually with `python scripts/<name>.py` from the backend root.

## Conventions

- **Import order (PEP 8)** — stdlib → third-party → local, blank line between groups, alphabetical within each group. The exceptions: `main.py` deliberately calls `load_dotenv()` *before* importing routers, because some routers read env vars at module load time.
- **Two-space indent** — the codebase uses 2-space indentation, not the Python default of 4. Match what's already in the file.
- **Pydantic for request bodies** — every POST/PATCH endpoint takes a `BaseModel` request type. Don't read fields out of `request.json()` directly.
- **`Depends(require_user)` for authenticated endpoints** — `services/auth.py::require_user` validates the Bearer JWT against Supabase and returns the auth user. Use the dependency rather than re-implementing token parsing.
- **Translate exceptions to user-friendly `detail`** — Supabase exceptions are noisy and leak implementation details. Catch them at the endpoint boundary and re-raise as `HTTPException` with a short, user-readable `detail` string + an appropriate status code. The frontend renders `err.detail` directly.
- **Service helpers handle the Supabase round-trip** — endpoints call `spend_tokens(user.id, n)`, not `supabase.table(...).select(...).update(...)` inline. Keeps the read-modify-write pattern in one place per resource.

## Tests

Run from the backend root with the venv active:

- `python -m pytest tests/ -v` — full suite (currently 21 cases across slots, migrations, account-tier validation).
- `python -m pytest tests/test_<file>.py` — one file.

Convention: tests live in `tests/` (not colocated next to source — different from the frontend), one `test_<module>.py` per module under test. They're hermetic — no real Supabase, no real Stripe. New endpoints/services should have their decision logic + boundary cases pinned with tests in this folder.

## Known follow-ups

The backend works but is rough around the edges. Before adding more features, consider polishing these — especially the first one if real-money flow grows:

1. **Lost-update race on JSONB columns (highest priority).** Every service that mutates `game_data` or `premium_game_data` does a read-modify-write in Python:

   ```python
   pgd = supabase.table(...).select("premium_game_data").eq(...).single().execute().data["premium_game_data"]
   pgd["tokens"] = pgd["tokens"] + amount
   supabase.table(...).update({"premium_game_data": pgd}).eq(...).execute()
   ```

   Two concurrent requests on different workers (e.g. the Stripe webhook crediting tokens while `/spin` is spending them) can both read the same starting value, and whichever update lands second silently wipes out the other's change. Real-money flow makes this a correctness issue, not just a polish item.

   Fix paths, in order of effort: a Postgres RPC function that does `update ... set premium_game_data = jsonb_set(premium_game_data, '{tokens}', (premium_game_data->>'tokens')::int + $1)` atomically; or pull the high-churn fields out of JSONB into proper columns and use `update users set tokens = tokens + $1`; or wrap each endpoint in a row-level lock (`select ... for update`) inside a transaction.

2. **No type annotations on most service functions.** Adding return types and arg types would let `mypy` (or just IDE inference) catch the kind of "forgot to handle a None" bug that currently only surfaces at runtime.

3. **No automatic migration runner / migration tests.** `services/migrations.py::ensure_user_data_complete` runs at login and the refresh button, which works but isn't a real migration system. As schema evolves, it'd be cleaner to have a `scripts/generate_migration.py` that creates dated migration files plus pytest cases for each. Listed here so we don't forget — `scripts/migrate_free_tier.py` was deleted as dead weight (it converted the old `account_tier == "free"` to `"account_tier_0"` and is no longer needed).

When picking up any of these, think about the *root cause* before patching the symptom (especially #1 — it's tempting to put a try/except around the symptom, but that just hides the corruption).
