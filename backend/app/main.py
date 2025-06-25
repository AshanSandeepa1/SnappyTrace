# app/main.py
from fastapi import FastAPI
from app.config import DATABASE_URL
from app.database import db
from app.auth.routes import router as auth_router

app = FastAPI()

@app.on_event("startup")
async def startup():
    await db.connect(DATABASE_URL)

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

app.include_router(auth_router, prefix="/auth")

@app.get("/ping")
def ping():
    return {"message": "pong"}

