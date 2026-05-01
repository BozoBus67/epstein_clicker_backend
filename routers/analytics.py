from fastapi import APIRouter, Depends

from services.analytics import capture as analytics_capture
from services.auth import require_user

router = APIRouter()

# Heartbeat from the frontend's active-time loop. The frontend POSTs this
# once every minute while the app is focused; counting these events in
# PostHog × the ping interval gives total active time per user.
@router.post("/active_ping")
def active_ping(user=Depends(require_user)):
  analytics_capture(distinct_id=user.id, event="active_ping")
  return {"status": "ok"}
