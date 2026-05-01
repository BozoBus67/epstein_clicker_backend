import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import stripe

# Load env BEFORE the routers import — some of them read env at module load time.
load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

from routers.account_tiers import router as account_tiers_router
from routers.analytics import router as analytics_router
from routers.auction_house import router as auction_house_router
from routers.buildings import router as buildings_router
from routers.chess import router as chess_router
from routers.gamble import router as gamble_router
from routers.game_data import router as game_data_router
from routers.mastery_scrolls import router as mastery_scrolls_router
from routers.payments import router as stripe_webhook_router
from routers.redeem.three_assumptions_poisson import router as three_assumptions_poisson_router
from routers.signup_and_login.login import router as login_router
from routers.signup_and_login.me import router as me_router
from routers.signup_and_login.signup import router as signup_router
from routers.tokens import router as tokens_router

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(stripe_webhook_router)
app.include_router(tokens_router)
app.include_router(auction_house_router)
app.include_router(mastery_scrolls_router)
app.include_router(signup_router)
app.include_router(login_router)
app.include_router(me_router)
app.include_router(account_tiers_router)
app.include_router(game_data_router)
app.include_router(gamble_router)
app.include_router(chess_router)
app.include_router(three_assumptions_poisson_router)
app.include_router(buildings_router)
app.include_router(analytics_router)

@app.get("/")
def root():
  return {"status": "ok"}