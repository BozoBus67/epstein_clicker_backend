from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import stripe
import os

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

from payments import router as payments_router
from tokens import router as tokens_router
from auction_house import router as auction_house_router
from mastery_scrolls import router as mastery_scrolls_router
from signup import router as signup_router

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(payments_router)
app.include_router(tokens_router)
app.include_router(auction_house_router)
app.include_router(mastery_scrolls_router)
app.include_router(signup_router)

@app.get("/")
def root():
  return {"status": "ok"}