import os

from posthog import Posthog

# Deliberate exception to the codebase's fail-loud-and-early principle.
#
# Analytics MUST NEVER break the user-facing request path: if PostHog is down,
# misconfigured, or simply not enabled in this environment (tests, local dev,
# a deploy whose env var was never set), a slot machine spin still has to
# succeed, deduct tokens, and award scrolls. So `capture()` is silent on
# failure by design.
#
# To keep the silence from hiding a real misconfiguration, we make the
# *startup* loud instead. The print below fires once at import time:
#   - "PostHog enabled" → key was found, events will flow.
#   - "PostHog DISABLED" → key was missing. Visible in `uvicorn` output
#     locally and in Render's deploy logs in production. If analytics ever
#     mysteriously goes dark, this line in the logs is the first thing to check.
# That moves the "loud failure" up to config-time (where it's actionable)
# without making it crash live requests (where it isn't).

_api_key = os.getenv("POSTHOG_API_KEY")
_host = os.getenv("POSTHOG_HOST")

# Both env vars are required — no defaults. There's no universally-correct
# default for `host` (US Cloud, EU Cloud, and self-hosted are all real
# choices), so a silent fallback would risk sending events to the wrong
# dataset. Treat the host the same way we treat the API key: explicit or off.
_missing = [k for k, v in (("POSTHOG_API_KEY", _api_key), ("POSTHOG_HOST", _host)) if not v]
if not _missing:
  client = Posthog(project_api_key=_api_key, host=_host)
  print(f"[analytics] PostHog enabled, host={_host}", flush=True)
else:
  client = None
  print(f"[analytics] PostHog DISABLED — missing env: {', '.join(_missing)}. Events will not be captured.", flush=True)

# `flush=True` on every print: Python's stdout is line-buffered when attached
# to a terminal but block-buffered inside Docker (Render's runtime). Without
# explicit flushing, these messages can sit in a buffer indefinitely and never
# appear in Render's log stream — which defeats the whole "fail loud at
# startup" point. uvicorn's own logger flushes correctly; only our raw prints
# are at risk.

def capture(distinct_id: str, event: str, properties: dict | None = None):
  if client is None:
    return
  try:
    client.capture(distinct_id=distinct_id, event=event, properties=properties or {})
    # Force the queued event out NOW instead of waiting for the SDK's 5-second
    # batch timer. On Render's free tier the worker can sleep or recycle inside
    # that window, killing queued events that never had a chance to flush.
    # Cost: ~50-150ms per request for the network round-trip to PostHog.
    # Acceptable at our scale (friends, low volume); revisit if traffic grows.
    client.flush()
  except Exception:
    print(f"[analytics] capture failed for event={event}", flush=True)
